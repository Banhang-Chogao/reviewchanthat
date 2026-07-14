(function() {
  'use strict';

  var GENERIC_LABELS = ['remain', 'khác', 'other', ''];

  var IncomeInsightsEngine = {
    analyze: function(transactions) {
      if (!transactions || transactions.length === 0) {
        return [{ level: 'info', text: 'Chưa có dữ liệu để phân tích. Hãy thêm các giao dịch để nhận nhận xét.' }];
      }

      var insights = [];
      var totalIncome = 0, totalDebt = 0;
      var debtByLabel = {}, incomeByLabel = {}, typeCount = {}, routeCount = {};
      var monthlyData = {};
      var now = new Date();
      var currentMonth = now.getMonth() + 1;
      var currentYear = now.getFullYear();

      for (var i = 0; i < transactions.length; i++) {
        var t = transactions[i];
        var inc = t.income || 0;
        var deb = t.debt || 0;
        totalIncome += inc;
        totalDebt += deb;

        var key = t.year + '-' + String(t.month).padStart(2, '0');
        if (!monthlyData[key]) monthlyData[key] = { income: 0, debt: 0, count: 0 };
        monthlyData[key].income += inc;
        monthlyData[key].debt += deb;
        monthlyData[key].count++;

        if (inc > 0 && t.incomeLabel) {
          incomeByLabel[t.incomeLabel] = (incomeByLabel[t.incomeLabel] || 0) + inc;
        }
        if (deb < 0 && t.debtLabel) {
          debtByLabel[t.debtLabel] = (debtByLabel[t.debtLabel] || 0) + deb;
        }
        if (t.transactionType && t.transactionType !== '/' && t.transactionType !== '-') {
          typeCount[t.transactionType] = (typeCount[t.transactionType] || 0) + 1;
        }
        if (t.route && t.route !== '/' && t.route !== '-') {
          routeCount[t.route] = (routeCount[t.route] || 0) + 1;
        }
      }

      var absDebt = Math.abs(totalDebt);
      var net = totalIncome + totalDebt;

      // 1. Debt/Income ratio
      if (totalIncome > 0) {
        var ratio = (absDebt / totalIncome) * 100;
        var ratioRounded = Math.round(ratio);
        if (ratioRounded > 50) {
          insights.push({
            level: 'danger',
            text: 'Tỷ lệ nợ đang chiếm ' + ratioRounded + '% thu nhập, cao hơn vùng an toàn. Cần rà soát các khoản nợ.'
          });
        } else if (ratioRounded > 30) {
          insights.push({
            level: 'warning',
            text: 'Tỷ lệ nợ đang chiếm ' + ratioRounded + '% thu nhập, ở mức trung bình.'
          });
        } else {
          insights.push({
            level: 'safe',
            text: 'Tỷ lệ nợ chỉ ' + ratioRounded + '% thu nhập, đang trong vùng an toàn.'
          });
        }
      }

      // 2. Largest debt source (with context)
      var sortedDebtLabels = Object.keys(debtByLabel).sort(function(a, b) {
        return debtByLabel[b] - debtByLabel[a];
      });
      if (sortedDebtLabels.length > 0) {
        var topDebtLabel = sortedDebtLabels[0];
        var topDebtAmt = Math.abs(debtByLabel[topDebtLabel]);
        var debtPct = absDebt > 0 ? Math.round((topDebtAmt / absDebt) * 100) : 0;
        var level = debtPct > 40 ? 'warning' : (debtPct > 20 ? 'info' : 'safe');
        insights.push({
          level: level,
          text: 'Khoản "' + topDebtLabel + '" là nhóm nợ lớn nhất — ' + formatVND(topDebtAmt) + (debtPct > 0 ? ' (chiếm ' + debtPct + '% tổng nợ).' : '.')
        });
      }

      // 3. Largest income source (skip generic labels)
      var sortedIncomeLabels = Object.keys(incomeByLabel)
        .filter(function(k) { return GENERIC_LABELS.indexOf(k.toLowerCase().trim()) === -1; })
        .sort(function(a, b) { return incomeByLabel[b] - incomeByLabel[a]; });
      if (sortedIncomeLabels.length === 0) {
        sortedIncomeLabels = Object.keys(incomeByLabel)
          .sort(function(a, b) { return incomeByLabel[b] - incomeByLabel[a]; });
      }
      if (sortedIncomeLabels.length > 0) {
        var topIncLabel = sortedIncomeLabels[0];
        var topIncAmt = incomeByLabel[topIncLabel];
        var incPct = totalIncome > 0 ? Math.round((topIncAmt / totalIncome) * 100) : 0;
        insights.push({
          level: 'safe',
          text: 'Nguồn thu nhập chính: "' + topIncLabel + '" — ' + formatVND(topIncAmt) + (incPct > 0 ? ' (chiếm ' + incPct + '% tổng thu nhập).' : '.')
        });
      }

      // 4. Net cash flow assessment
      if (net > 0) {
        insights.push({
          level: 'safe',
          text: 'Thu nhập vẫn đủ bù nghĩa vụ nợ, còn dư ' + formatVND(net) + '.'
        });
      } else if (net < 0) {
        insights.push({
          level: 'danger',
          text: 'Chi tiêu đang vượt thu nhập ' + formatVND(Math.abs(net)) + '. Cần cắt giảm nợ hoặc tăng thu nhập.'
        });
      } else {
        insights.push({
          level: 'info',
          text: 'Thu nhập vừa đủ bù nghĩa vụ nợ, không còn dư.'
        });
      }

      // 5. Cash flow decline (month-over-month)
      var months = Object.keys(monthlyData).sort();
      if (months.length >= 2) {
        var lastTwo = months.slice(-2);
        var prev = monthlyData[lastTwo[0]];
        var current = monthlyData[lastTwo[1]];
        if (prev && current) {
          var prevNet = prev.income + prev.debt;
          var currNet = current.income + current.debt;
          if (prevNet > 0 && currNet < prevNet) {
            var decline = ((prevNet - currNet) / prevNet) * 100;
            if (decline > 20) {
              insights.push({
                level: 'warning',
                text: 'Dòng tiền ròng giảm ' + Math.round(decline) + '% so với tháng trước. Theo dõi xu hướng này.'
              });
            }
          }
        }
      }

      // 6. Concentration risk (single income source)
      if (sortedIncomeLabels.length > 0 && totalIncome > 0) {
        var topIncomeAmt = incomeByLabel[sortedIncomeLabels[0]];
        var concentration = (topIncomeAmt / totalIncome) * 100;
        if (concentration > 80) {
          insights.push({
            level: 'warning',
            text: 'Thu nhập tập trung chủ yếu từ "' + sortedIncomeLabels[0] + '" (' + Math.round(concentration) + '%). Cân nhắc đa dạng hóa nguồn thu.'
          });
        }
      }

      // 7. Recurring labels (skip generic, show top 5)
      var labelCount = {};
      for (var j = 0; j < transactions.length; j++) {
        var lb = transactions[j].debtLabel || transactions[j].incomeLabel || '';
        if (lb && GENERIC_LABELS.indexOf(lb.toLowerCase().trim()) === -1) {
          labelCount[lb] = (labelCount[lb] || 0) + 1;
        }
      }
      var recurringLabels = Object.keys(labelCount)
        .filter(function(k) { return labelCount[k] >= 3; })
        .sort(function(a, b) { return labelCount[b] - labelCount[a]; })
        .slice(0, 5);
      if (recurringLabels.length > 0) {
        insights.push({
          level: 'info',
          text: 'Các nhóm chi tiêu lặp lại: ' + recurringLabels.join(', ') + '.'
        });
      }

      // 8. Unusual transaction detection (z-score-like)
      var amounts = [];
      for (var k = 0; k < transactions.length; k++) {
        var a = Math.abs(transactions[k].income || 0) + Math.abs(transactions[k].debt || 0);
        if (a > 0) amounts.push(a);
      }
      if (amounts.length >= 5) {
        var sum = 0, mean = 0, sqDiff = 0, stdDev = 0;
        for (var n = 0; n < amounts.length; n++) sum += amounts[n];
        mean = sum / amounts.length;
        for (var m = 0; m < amounts.length; m++) sqDiff += Math.pow(amounts[m] - mean, 2);
        stdDev = Math.sqrt(sqDiff / amounts.length);
        if (stdDev > 0) {
          var flagged = false;
          for (var p = 0; p < transactions.length && !flagged; p++) {
            var val = Math.abs(transactions[p].income || 0) + Math.abs(transactions[p].debt || 0);
            var z = (val - mean) / stdDev;
            if (z > 2.5 && val > 50000) {
              var label = transactions[p].incomeLabel || transactions[p].debtLabel || transactions[p].remark || '';
              insights.push({
                level: 'warning',
                text: 'Phát hiện giao dịch bất thường: ' + formatVND(val) + (label ? ' (' + label + ')' : '') + '.'
              });
              flagged = true;
            }
          }
        }
      }

      // 9. Preferred route/type (skip empty/placeholder)
      var sortedRoutes = Object.keys(routeCount).sort(function(a, b) { return routeCount[b] - routeCount[a]; });
      if (sortedRoutes.length > 0) {
        var topRoute = sortedRoutes[0];
        var routePct = transactions.length > 0 ? Math.round((routeCount[topRoute] / transactions.length) * 100) : 0;
        insights.push({
          level: 'info',
          text: 'Bạn có xu hướng thanh toán qua "' + topRoute + '" nhiều nhất (' + routeCount[topRoute] + ' giao dịch, ' + routePct + '%).'
        });
      } else {
        insights.push({
          level: 'info',
          text: 'Chưa ghi nhận kênh thanh toán cụ thể.'
        });
      }

      var sortedTypes = Object.keys(typeCount).sort(function(a, b) { return typeCount[b] - typeCount[a]; });
      if (sortedTypes.length > 0) {
        var topType = sortedTypes[0];
        var typePct = transactions.length > 0 ? Math.round((typeCount[topType] / transactions.length) * 100) : 0;
        insights.push({
          level: 'info',
          text: 'Loại giao dịch thường dùng: "' + topType + '" (' + typeCount[topType] + ' lần, ' + typePct + '%).'
        });
      }

      // 10. Warning threshold check (contextual: check value vs monthly income)
      if (transactions.length >= 3) {
        var largeDebts = [];
        for (var q = 0; q < transactions.length; q++) {
          var d = Math.abs(transactions[q].debt || 0);
          if (d > 5000000) {
            largeDebts.push({
              amount: d,
              label: transactions[q].debtLabel || transactions[q].remark || '',
              month: transactions[q].month,
              year: transactions[q].year
            });
          }
        }
        if (largeDebts.length === 0) {
          insights.push({
            level: 'safe',
            text: 'Không có khoản chi nào vượt ngưỡng 5.000.000₫.'
          });
        } else {
          var avgMonthlyIncome = 0;
          var monthKeys = Object.keys(monthlyData);
          if (monthKeys.length > 0) {
            var sumMonthly = 0;
            for (var r = 0; r < monthKeys.length; r++) sumMonthly += monthlyData[monthKeys[r]].income;
            avgMonthlyIncome = sumMonthly / monthKeys.length;
          }
          if (largeDebts.length === 1 && avgMonthlyIncome > 0) {
            var debtRatio = (largeDebts[0].amount / avgMonthlyIncome) * 100;
            if (debtRatio > 50) {
              insights.push({
                level: 'warning',
                text: 'Có khoản chi ' + formatVND(largeDebts[0].amount) + (largeDebts[0].label ? ' ("' + largeDebts[0].label + '")' : '') + ' — tương đương ' + Math.round(debtRatio) + '% thu nhập trung bình tháng. Kiểm tra lại.'
              });
            } else {
              insights.push({
                level: 'info',
                text: 'Có khoản chi lớn ' + formatVND(largeDebts[0].amount) + (largeDebts[0].label ? ' ("' + largeDebts[0].label + '")' : '') + ', nhưng vẫn trong tầm kiểm soát (chiếm ' + Math.round(debtRatio) + '% thu nhập trung bình).'
              });
            }
          } else if (largeDebts.length > 1) {
            insights.push({
              level: 'warning',
              text: 'Có ' + largeDebts.length + ' khoản chi vượt ngưỡng 5.000.000₫. Kiểm tra tổng thể các khoản lớn.'
            });
          } else {
            insights.push({
              level: 'warning',
              text: 'Có khoản chi vượt ngưỡng 5.000.000₫. Kiểm tra lại.'
            });
          }
        }
      }

      // 11. Emergency reserve suggestion
      if (net > 0) {
        var monthlyExpense = 0;
        var monthKeys2 = Object.keys(monthlyData);
        if (monthKeys2.length > 0) {
          var sumExpense = 0;
          for (var s = 0; s < monthKeys2.length; s++) sumExpense += Math.abs(monthlyData[monthKeys2[s]].debt);
          monthlyExpense = sumExpense / monthKeys2.length;
        }
        if (monthlyExpense > 0) {
          var reserveNeeded = monthlyExpense * 3;
          var currentReserve = net > reserveNeeded ? net : net;
          insights.push({
            level: currentReserve >= reserveNeeded ? 'safe' : 'info',
            text: currentReserve >= reserveNeeded
              ? 'Quỹ dự phòng hiện tại (' + formatVND(net) + ') đủ trang trải ' + Math.round(net / monthlyExpense) + ' tháng chi phí. Tốt cho khẩn cấp.'
              : 'Duy trì quỹ dự phòng khẩn cấp tối thiểu 3 tháng chi phí (~' + formatVND(monthlyExpense * 3) + ').'
          });
        } else {
          insights.push({
            level: 'info',
            text: 'Duy trì quỹ dự phòng khẩn cấp tối thiểu 3-6 tháng chi phí sinh hoạt.'
          });
        }
      }

      // 12. Monthly expense trend
      if (monthKeys2 && monthKeys2.length >= 3) {
        var recentMonths = monthKeys2.slice(-3);
        var expenses = recentMonths.map(function(m) { return Math.abs(monthlyData[m].debt); });
        if (expenses[2] > expenses[0] && expenses[2] > expenses[1]) {
          var trendPct = expenses[0] > 0 ? Math.round(((expenses[2] - expenses[0]) / expenses[0]) * 100) : 0;
          if (trendPct > 30) {
            insights.push({
              level: 'warning',
              text: 'Chi tiêu 3 tháng gần đây có xu hướng tăng (' + trendPct + '%). Rà soát lại các khoản chưa cần thiết.'
            });
          }
        }
      }

      // 13. Safety state
      var safetyRatio = totalIncome > 0 ? (absDebt / totalIncome) : 1;
      var safetyState = safetyRatio <= 0.3 ? 'safe' : (safetyRatio <= 0.5 ? 'warning' : 'danger');
      var safetyText = '';
      if (safetyState === 'safe') {
        safetyText = 'Điểm an toàn tài chính: Tốt. Duy trì tỷ lệ nợ dưới 30% thu nhập.';
      } else if (safetyState === 'warning') {
        safetyText = 'Điểm an toàn tài chính: Trung bình. Tỷ lệ nợ đang ở mức cần theo dõi.';
      } else {
        safetyText = 'Điểm an toàn tài chính: Cảnh báo. Tỷ lệ nợ cao, cần cắt giảm.';
      }
      insights.push({ level: safetyState, text: safetyText });

      // 14. Insufficient data warning
      if (transactions.length < 5) {
        insights.push({
          level: 'info',
          text: 'Dữ liệu chưa đủ để kết luận xu hướng. Cần ít nhất 5 giao dịch.'
        });
      }

      return insights;
    }
  };

  function formatVND(amount) {
    return Math.round(amount).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') + '₫';
  }

  if (typeof window !== 'undefined') {
    window.IncomeInsightsEngine = IncomeInsightsEngine;
  }
})();
