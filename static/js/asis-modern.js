(function () {
  function onReady(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  onReady(function () {
    document.querySelectorAll('[data-asis-sidebar-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.body.classList.toggle('asis-sidebar-open');
      });
    });
    document.querySelectorAll('.asis-sidebar-backdrop, .asis-nav-link').forEach(function (el) {
      el.addEventListener('click', function () {
        document.body.classList.remove('asis-sidebar-open');
      });
    });

    var clock = document.querySelector('[data-asis-clock]');
    if (clock) {
      var updateClock = function () {
        var now = new Date();
        clock.textContent = now.toLocaleString('az-AZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      };
      updateClock();
      setInterval(updateClock, 30000);
    }

    document.querySelectorAll('.content-container').forEach(function (container) {
      var tables = Array.prototype.slice.call(container.querySelectorAll('.table-responsive > table, .table-responsive table')).filter(function (table) {
        return table.tBodies && table.tBodies.length && !table.closest('.modal') && !table.dataset.noAutoSearch;
      });
      tables.forEach(function (table, index) {
        var wrap = table.closest('.table-responsive');
        if (!wrap || wrap.dataset.searchAttached === '1') return;
        wrap.dataset.searchAttached = '1';

        var rows = Array.prototype.slice.call(table.tBodies[0].rows).filter(function (row) {
          return !row.classList.contains('expense-details-row') && !row.classList.contains('collapse');
        });
        if (rows.length < 6) return;

        var bar = document.createElement('div');
        bar.className = 'asis-auto-search';
        bar.innerHTML = '<div class="input-group input-group-sm"><span class="input-group-text"><i class="fas fa-search"></i></span><input type="search" class="form-control" placeholder="Sürətli axtarış: nömrə, ad, tarix, xərc tipi..."></div><div class="asis-auto-count"></div>';
        wrap.parentNode.insertBefore(bar, wrap);
        var input = bar.querySelector('input');
        var count = bar.querySelector('.asis-auto-count');

        var update = function () {
          var q = input.value.trim().toLocaleLowerCase('az-AZ');
          var shown = 0;
          rows.forEach(function (row) {
            var hit = !q || row.innerText.toLocaleLowerCase('az-AZ').indexOf(q) !== -1;
            row.style.display = hit ? '' : 'none';
            shown += hit ? 1 : 0;
            var target = row.getAttribute('data-bs-target');
            if (!hit && target) {
              var details = document.querySelector(target);
              if (details) details.style.display = 'none';
            } else if (hit) {
              var target2 = row.getAttribute('data-bs-target');
              if (target2) {
                var details2 = document.querySelector(target2);
                if (details2) details2.style.display = '';
              }
            }
          });
          count.textContent = shown + ' / ' + rows.length + ' sətir';
        };
        input.addEventListener('input', update);
        update();
      });
    });

    document.querySelectorAll('table').forEach(function (table) {
      if (!table.classList.contains('align-middle')) table.classList.add('align-middle');
    });


    document.querySelectorAll('[data-asis-filter-wrap]').forEach(function (wrap) {
      var input = wrap.querySelector('[data-asis-filter-input]');
      var grid = wrap.parentElement.querySelector('[data-asis-filter-grid]');
      if (!input || !grid) return;
      var items = Array.prototype.slice.call(grid.querySelectorAll('[data-asis-filter-item]'));
      input.addEventListener('input', function () {
        var q = input.value.trim().toLocaleLowerCase('az-AZ');
        items.forEach(function (item) {
          item.style.display = !q || item.innerText.toLocaleLowerCase('az-AZ').indexOf(q) !== -1 ? '' : 'none';
        });
      });
    });
  });
})();
