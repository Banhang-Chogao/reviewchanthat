(function() {
  'use strict';

  var IncomeInsightsEngine = {
    analyze: function(transactions) {
      if (!transactions || transactions.length === 0) {
        return [{ level: 'info', text: 'Chưa có dữ liệu để phân tích. Hãy thêm các giao dịch để nhận nhận xét.' }];
      }

      var insights = [];
      var totalIncome = 0, totalDebt = 0;
      var debtByLabel = {}, incomeByLabel = {}, typeCount = {}, routeCount = {};
      var monthlyData = {};
      var dailyData = {};
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

        var dayKey = t.year + '-' + String(t.month).padStart(2, '0') + '-' + String(t.day).padStart(2, '0');
        if (!dailyData[dayKey]) dailyData[dayKey] = { income: 0, debt: 0 };
        dailyData[dayKey].income += inc;
        dailyData[dayKey].debt += deb;

        if (inc > 0 && t.incomeLabel) {
          incomeByLabel[t.incomeLabel] = (incomeByLabel[t.incomeLabel] || 0) + inc;
        }
        if (deb < 0 && t.debtLabel) {
          debtByLabel[t.debtLabel] = (debtByLabel[t.debtLabel] || 0) + deb;
        }
        if (t.transactionType) {
          typeCount[t.transactionType] = (typeCount[t.transactionType] || 0) + 1;
        }
        if (t.route) {
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
            text: 'Tỷ lệ nợ đang chiếm ' + ratioRounded + '% thu nhập, cao hơn vùng an toàn tự đặt. Cần rà soát các khoản nợ.'
          });
        } else if (ratioRounded > 30) {
          insights.push({
            level: 'warning',
            text: 'Tỷ lệ nợ tháng này đang chiếm ' + ratioRounded + '% thu nhập, cao hơn vùng an toàn tự đặt.'
          });
        } else {
          insights.push({
            level: 'safe',
            text: 'Tỷ lệ nợ chỉ ' + ratioRounded + '% thu nhập, đang trong vùng an toàn.'
          });
        }
      }

      // 2. Largest debt source
      var sortedDebtLabels = Object.keys(debtByLabel).sort(function(a, b) {
        return debtByLabel[b] - debtByLabel[a];
      });
      if (sortedDebtLabels.length > 0) {
        var topDebtLabel = sortedDebtLabels[0];
        var topDebtAmt = Math.abs(debtByLabel[topDebtLabel]);
        insights.push({
          level: 'warning',
          text: 'Khoản "' + topDebtLabel + '" đang là nhóm nợ lớn nhất (' + formatVND(topDebtAmt) + ').'
        });
      }

      // 3. Largest income source
      var sortedIncomeLabels = Object.keys(incomeByLabel).sort(function(a, b) {
        return incomeByLabel[b] - incomeByLabel[a];
      });
      if (sortedIncomeLabels.length > 0) {
        var topIncLabel = sortedIncomeLabels[0];
        insights.push({
          level: 'safe',
          text: 'Nguồn thu nhập chính: "' + topIncLabel + '" (' + formatVND(incomeByLabel[topIncLabel]) + ').'
        });
      }

      // 4. Net cash flow assessment
      if (net > 0) {
        insights.push({
          level: 'safe',
          text: 'Thu nhập vẫn đủ bù nghĩa vụ nợ, phần còn lại là ' + formatVND(net) + '.'
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
                text: 'Dòng tiền ròng đang giảm ' + Math.round(decline) + '% so với tháng trước. Theo dõi xu hướng này.'
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

      // 7. Recurring labels
      var labelCount = {};
      for (var j = 0; j < transactions.length; j++) {
        var lb = transactions[j].debtLabel || transactions[j].incomeLabel || '';
        if (lb) {
          labelCount[lb] = (labelCount[lb] || 0) + 1;
        }
      }
      var recurringLabels = Object.keys(labelCount).filter(function(k) { return labelCount[k] >= 3; });
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
          for (var p = 0; p < transactions.length; p++) {
            var val = Math.abs(transactions[p].income || 0) + Math.abs(transactions[p].debt || 0);
            var z = (val - mean) / stdDev;
            if (z > 2.5 && val > 50000) {
              var label = transactions[p].incomeLabel || transactions[p].debtLabel || transactions[p].remark || '';
              insights.push({
                level: 'warning',
                text: 'Phát hiện giao dịch bất thường: ' + formatVND(val) + (label ? ' (' + label + ')' : '') + '.'
              });
              break;
            }
          }
        }
      }

      // 9. Preferred route/type
      var sortedRoutes = Object.keys(routeCount).sort(function(a, b) { return routeCount[b] - routeCount[a]; });
      if (sortedRoutes.length > 0) {
        insights.push({
          level: 'info',
          text: 'Bạn có xu hướng thanh toán qua "' + sortedRoutes[0] + '" nhiều nhất (' + routeCount[sortedRoutes[0]] + ' giao dịch).'
        });
      }

      var sortedTypes = Object.keys(typeCount).sort(function(a, b) { return typeCount[b] - typeCount[a]; });
      if (sortedTypes.length > 0) {
        insights.push({
          level: 'info',
          text: 'Loại giao dịch thường dùng: "' + sortedTypes[0] + '" (' + typeCount[sortedTypes[0]] + ' lần).'
        });
      }

      // 10. Warning threshold check
      if (transactions.length >= 3) {
        var thresholdWarn = false;
        for (var q = 0; q < transactions.length; q++) {
          var d = Math.abs(transactions[q].debt || 0);
          if (d > 5000000) {
            thresholdWarn = true;
            break;
          }
        }
        if (!thresholdWarn) {
          insights.push({
            level: 'safe',
            text: 'Chưa có khoản chi nào vượt ngưỡng cảnh báo (5.000.000).'
          });
        } else {
          insights.push({
            level: 'warning',
            text: 'Có khoản chi vượt ngưỡng 5.000.000. Kiểm tra lại.'
          });
        }
      }

      // 11. Missing emergency reserve suggestion
      if (net > 0) {
        insights.push({
          level: 'info',
          text: 'Duy trì quỹ dự phòng khẩn cấp tối thiểu 3-6 tháng chi phí sinh hoạt.'
        });
      }

      // 12. Safety state
      var safetyRatio = totalIncome > 0 ? (absDebt / totalIncome) : 1;
      var safetyState = safetyRatio <= 0.3 ? 'safe' : (safetyRatio <= 0.5 ? 'warning' : 'danger');
      var safetyText = '';
      if (safetyState === 'safe') {
        safetyText = 'Điểm an toàn tài chính: Tốt. Duy trì tỷ lệ nợ dưới 30% thu nhập.';
      } else if (safetyState === 'warning') {
        safetyText = 'Điểm an toàn tài chính: Cần theo dõi. Tỷ lệ nợ đang ở mức trung bình.';
      } else {
        safetyText = 'Điểm an toàn tài chính: Cảnh báo. Tỷ lệ nợ cao, cần cắt giảm.';
      }
      insights.push({ level: safetyState, text: safetyText });

      // 13. Insufficient data warning
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
