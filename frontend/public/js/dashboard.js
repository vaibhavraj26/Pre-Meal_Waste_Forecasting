// Dashboard Page Controller

let wasteTrendChart = null;

async function loadDashboard() {
  try {
    const stats = await API.get('/dashboard/stats');
    renderKPIs(stats);
    renderTrendChart(stats.recent_trend || []);
    loadRecentMealsTable();
  } catch (err) {
    console.error('Error loading dashboard stats:', err);
    showToast('Dashboard Error', 'Could not fetch dashboard statistics from MongoDB.', 'danger');
  }
}

function renderKPIs(stats) {
  document.getElementById('stat-total-meals').textContent = (stats.total_meals || 0).toLocaleString();
  document.getElementById('stat-total-prepared').textContent = (stats.total_prepared_kg || 0).toLocaleString() + ' kg';
  document.getElementById('stat-total-wasted').textContent = (stats.total_wasted_kg || 0).toLocaleString() + ' kg';
  document.getElementById('stat-avg-waste').textContent = (stats.avg_waste_percentage || 0) + '%';

  const highCount = stats.high_waste_count || 0;
  const lowCount = stats.low_waste_count || 0;
  const total = stats.total_meals || 1;
  const highPct = Math.round((highCount / total) * 100);

  document.getElementById('stat-high-waste-detail').textContent = `${highCount} High Waste (${highPct}%)`;
  document.getElementById('stat-low-waste-detail').textContent = `${lowCount} Low Waste (${100 - highPct}%)`;
}

function renderTrendChart(trendData) {
  const ctx = document.getElementById('dashboardTrendChart');
  if (!ctx) return;

  const labels = trendData.map(d => `${d.date} (${d.meal_type})`);
  const values = trendData.map(d => d.waste_percentage);
  const colors = trendData.map(d => d.waste_percentage > 15 ? '#ef4444' : '#10b981');

  if (wasteTrendChart) {
    wasteTrendChart.destroy();
  }

  wasteTrendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Waste Percentage (%)',
          data: values,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          pointBackgroundColor: colors,
          pointBorderColor: colors,
          pointRadius: 5,
          pointHoverRadius: 7,
          fill: true,
          tension: 0.3
        },
        {
          label: 'High Waste Threshold (15%)',
          data: labels.map(() => 15.0),
          borderColor: '#ef4444',
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: 'Waste Percentage (%)' },
          suggestedMax: 35
        },
        x: {
          ticks: {
            maxRotation: 45,
            minRotation: 30,
            autoSkip: true,
            maxTicksLimit: 10
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${context.parsed.y}%`;
            }
          }
        }
      }
    }
  });
}

async function loadRecentMealsTable() {
  const tbody = document.getElementById('recent-meals-tbody');
  if (!tbody) return;

  try {
    const data = await API.get('/meals?limit=6&sort_by=date&sort_order=-1');
    const records = data.records || [];

    if (records.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No meal records found in MongoDB.</td></tr>';
      return;
    }

    tbody.innerHTML = records.map(meal => {
      const isHigh = meal.waste_level === 'HIGH';
      const badge = isHigh
        ? `<span class="badge-high-waste"><i class="bi bi-exclamation-triangle-fill"></i> HIGH (${meal.waste_percentage}%)</span>`
        : `<span class="badge-low-waste"><i class="bi bi-check-circle-fill"></i> LOW (${meal.waste_percentage}%)</span>`;

      const menuText = Array.isArray(meal.menu_items) ? meal.menu_items.join(', ') : (meal.menu_items || 'Standard Menu');

      return `
        <tr>
          <td><strong>${meal.date}</strong></td>
          <td><span class="badge bg-secondary">${meal.meal_type}</span></td>
          <td>${menuText}</td>
          <td>${meal.food_prepared_kg} kg</td>
          <td>${meal.food_consumed_kg} kg</td>
          <td>${meal.leftover_food_kg} kg</td>
          <td>${badge}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading recent meals table:', err);
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger py-4">Error loading records from database.</td></tr>';
  }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
