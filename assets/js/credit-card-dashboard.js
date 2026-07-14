(function(){
  'use strict';

  var app = document.getElementById('ccd-app');
  if (!app) return;

  // ── Payment Progress ──
  function initProgress() {
    var fill = document.getElementById('ccd-progress-fill');
    var pctEl = document.getElementById('ccd-progress-percent');
    var section = document.querySelector('.ccd-payment-progress');
    if (!fill || !pctEl || !section) return;

    var pct = 50;
    fill.style.width = pct + '%';
    pctEl.textContent = pct + '%';

    if (pct > 90) {
      section.dataset.status = 'overdue';
    } else if (pct > 70) {
      section.dataset.status = 'warning';
    } else {
      section.dataset.status = 'normal';
    }
  }

  // ── Spending trend bars - set heights from data attributes ──
  function initTrendBars() {
    var bars = document.querySelectorAll('.ccd-spending__trend-bar span');
    bars.forEach(function(span) {
      var h = span.getAttribute('style') || '';
      // style is already set inline; we ensure it's applied
    });
  }

  // ── Simulate typing effect for AI responses ──
  function typeMessage(container, text, callback) {
    var msg = document.createElement('div');
    msg.className = 'ccd-assistant__message ccd-assistant__message--bot';
    container.appendChild(msg);

    var i = 0;
    function type() {
      if (i < text.length) {
        msg.textContent += text.charAt(i);
        i++;
        setTimeout(type, 15 + Math.random() * 20);
      } else {
        if (callback) callback();
      }
    }
    type();
  }

  // ── AI Assistant ──
  function initAssistant() {
    var input = document.getElementById('ccd-assistant-input');
    var sendBtn = document.getElementById('ccd-assistant-send');
    var messages = document.getElementById('ccd-assistant-messages');
    var prompts = document.querySelectorAll('.ccd-assistant__prompt');
    if (!input || !sendBtn || !messages) return;

    var isTyping = false;
    var responses = {
      'what is the best card for travel': 'For travel, we recommend the HSBC Visa Signature. It offers:\n• 2x reward points on flight & hotel bookings\n• Free travel insurance\n• No foreign transaction fees\n• Airport lounge access (4x/year)',
      'why is my cashback lower this month': 'Your cashback is lower this month because:\n1. You spent 32% less in bonus categories (groceries, dining)\n2. You missed the 5% cashback cap at supermarkets\n\nTip: Spend 650,000 VND at supermarkets to unlock 5% cashback.',
      'how can i avoid late fees': 'To avoid late fees:\n• Set up auto-pay from your HSBC account\n• Enable payment reminders (we recommend 5 days before due date)\n• Link your account to receive SMS alerts\n\nYour next payment is due on 25/05 — 5 days from now.'
    };

    function getResponse(text) {
      var lower = text.toLowerCase().trim();
      // exact match first
      if (responses[lower]) return responses[lower];
      // partial match
      for (var key in responses) {
        if (lower.indexOf(key) !== -1) {
          return responses[key];
        }
      }
      return 'Thanks for your question! I recommend checking the HSBC website or contacting customer support for the most accurate information about this topic.';
    }

    function addUserMessage(text) {
      var msg = document.createElement('div');
      msg.className = 'ccd-assistant__message ccd-assistant__message--user';
      msg.textContent = text;
      messages.appendChild(msg);
      messages.scrollTop = messages.scrollHeight;
    }

    function handleSend() {
      if (isTyping) return;
      var text = input.value.trim();
      if (!text) return;
      addUserMessage(text);
      input.value = '';
      isTyping = true;

      typeMessage(messages, getResponse(text), function() {
        isTyping = false;
        messages.scrollTop = messages.scrollHeight;
      });
    }

    sendBtn.addEventListener('click', handleSend);
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') handleSend();
    });

    prompts.forEach(function(btn) {
      btn.addEventListener('click', function() {
        if (isTyping) return;
        var text = this.getAttribute('data-prompt');
        if (text) {
          addUserMessage(text.replace(/^"|"$/g, ''));
          isTyping = true;
          typeMessage(messages, getResponse(text), function() {
            isTyping = false;
            messages.scrollTop = messages.scrollHeight;
          });
        }
      });
    });
  }

  // ── Quick Actions (simulated) ──
  function initQuickActions() {
    var btns = document.querySelectorAll('.ccd-actions__btn');
    btns.forEach(function(btn) {
      btn.addEventListener('click', function() {
        var text = this.textContent.trim();
        if (text.indexOf('Pay Now') !== -1) {
          alert('💳 Redirecting to payment gateway...');
        } else if (text.indexOf('Download Statement') !== -1) {
          alert('📄 Generating PDF statement...');
        } else if (text.indexOf('Copy Card Number') !== -1) {
          // Simulate copy
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText('**** **** **** 1234').then(function() {
              btn.textContent = '✅ Copied!';
              setTimeout(function() { btn.textContent = text; }, 2000);
            });
          } else {
            alert('📋 Card number copied: **** **** **** 1234');
          }
        } else if (text.indexOf('Lock Card') !== -1) {
          if (confirm('🔒 Are you sure you want to lock this card?')) {
            btn.textContent = '🔒 Card Locked';
            btn.disabled = true;
          }
        } else if (text.indexOf('Manage Limits') !== -1) {
          alert('⚙ Opening credit limit settings...');
        }
      });
    });
  }

  // ── Simulate notification refresh ──
  function initNotifications() {
    var notifList = document.getElementById('ccd-notifications');
    if (!notifList) return;

    // No real-time updates; static for now
  }

  // ── Intersection Observer for cards ──
  function initReveal() {
    var cards = document.querySelectorAll('.ccd-card');
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    }, { threshold: 0.08 });

    cards.forEach(function(card, i) {
      card.style.opacity = '0';
      card.style.transform = 'translateY(16px)';
      card.style.transition = 'opacity .5s ease, transform .5s ease';
      card.style.transitionDelay = (i * 0.05) + 's';
      observer.observe(card);
    });
  }

  // ── Init ──
  initProgress();
  initTrendBars();
  initAssistant();
  initQuickActions();
  initNotifications();

  // Delay reveal to allow paint
  if (window.requestAnimationFrame) {
    requestAnimationFrame(function() {
      setTimeout(initReveal, 100);
    });
  } else {
    initReveal();
  }

})();
