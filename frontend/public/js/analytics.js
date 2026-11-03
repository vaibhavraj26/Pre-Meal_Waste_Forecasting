// Analytics Hub & Interactive Chart.js Visualizations Controller

let dailyChart = null;
let mealTypeChart = null;
let weekdayChart = null;
let topItemsChart = null;
let categoryChart = null;

async function loadAnalytics() {
  try {
    const data = await API.get('/analytics');
    renderDailyTrendChart(data.daily_trend || []);
    renderMealTypeChart(data.meal_type_waste || []);
    renderWeekdayChart(data.weekday_waste || []);
    renderTopItemsChart(data.top_wasted_items || []);
    renderCategoryChart(data.category_waste || []);
    renderPredictedVsActual(data.predicted_vs_actual || []);
  } catch (err) {
    console.error('Error loading analytics:', err);
    showToast('Analytics Error', 'Could not fetch analytics data from MongoDB.', 'danger');
  }
}

function renderDailyTrendChart(dailyData) {
  const ctx = document.getElementById('dailyTrendChart');
  if (!ctx) return;

  const labels = dailyData.map(d => d.date);
  const wastePcts = dailyData.map(d => d.avg_waste_percentage);
  const wastedKg = dailyData.map(d => d.total_wasted_kg);

  if (dailyChart) dailyChart.destroy();

  dailyChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Daily Average Waste (%)',
          data: wastePcts,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.15)',
          fill: true,
          tension: 0.3,
          yAxisID: 'y'
        },
        {
          label: 'Total Leftover Wasted (kg)',
          data: wastedKg,
          borderColor: '#ef4444',
          backgroundColor: '#ef4444',
          type: 'bar',
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: { display: true, text: 'Waste Rate (%)' },
          beginAtZero: true
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          title: { display: true, text: 'Wasted Food (kg)' },
          grid: { drawOnChartArea: false },
          beginAtZero: true
        },
        x: {
          ticks: { maxRotation: 45, autoSkip: true, maxTicksLimit: 12 }
        }
      }
    }
  });
}

function renderMealTypeChart(mealData) {
  const ctx = document.getElementById('mealTypeChart');
  if (!ctx) return;

  const labels = mealData.map(m => m.meal_type);
  const data = mealData.map(m => m.avg_waste_percentage);
  const colors = ['#3b82f6', '#f59e0b', '#10b981'];

  if (mealTypeChart) mealTypeChart.destroy();

  mealTypeChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Average Waste Percentage (%)',
        data: data,
        backgroundColor: colors,
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, suggestedMax: 25, title: { display: true, text: 'Avg Waste %' } }
      }
    }
  });
}

function renderWeekdayChart(weekdayData) {
  const ctx = document.getElementById('weekdayChart');
  if (!ctx) return;

  const labels = weekdayData.map(w => w.day);
  const data = weekdayData.map(w => w.avg_waste_percentage);
  const colors = labels.map(day => (day === 'Saturday' || day === 'Sunday') ? '#ef4444' : '#3b82f6');

  if (weekdayChart) weekdayChart.destroy();

  weekdayChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Avg Waste % (Red = Weekend)',
        data: data,
        backgroundColor: colors,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, suggestedMax: 25, title: { display: true, text: 'Avg Waste %' } }
      }
    }
  });
}

function renderTopItemsChart(itemData) {
  const ctx = document.getElementById('topItemsChart');
  if (!ctx) return;

  const labels = itemData.map(i => i.item_name);
  const data = itemData.map(i => i.avg_waste_percentage);

  if (topItemsChart) topItemsChart.destroy();

  topItemsChart = new Chart(ctx, {
    type: 'bar',
    indexAxis: 'y',
    data: {
      labels: labels,
      datasets: [{
        label: 'Avg Waste Percentage (%)',
        data: data,
        backgroundColor: '#f87171',
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { beginAtZero: true, suggestedMax: 30, title: { display: true, text: 'Waste %' } }
      }
    }
  });
}

function renderCategoryChart(catData) {
  const ctx = document.getElementById('categoryChart');
  if (!ctx) return;

  const labels = catData.map(c => c.category);
  const data = catData.map(c => c.avg_waste_percentage);
  const colors = ['#6366f1', '#ec4899', '#f97316', '#14b8a6', '#8b5cf6'];

  if (categoryChart) categoryChart.destroy();

  categoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  });
}

function renderPredictedVsActual(predData) {
  const tbody = document.getElementById('pred-actual-tbody');
  if (!tbody) return;

  if (predData.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No prediction logs recorded yet. Run predictions through the "Predict Waste" module.</td></tr>';
    return;
  }

  tbody.innerHTML = predData.map(p => {
    const isPredHigh = p.predicted_waste_level === 'HIGH';
    const isActHigh = p.actual_waste_level === 'HIGH';
    const match = isPredHigh === isActHigh;

    return `
      <tr>
        <td><strong>${p.date}</strong></td>
        <td><span class="badge bg-secondary">${p.meal_type}</span></td>
        <td>
          <span class="badge ${isPredHigh ? 'bg-danger' : 'bg-success'}">
            ${p.predicted_waste_level || 'LOW'} (${p.predicted_high_prob}%)
          </span>
        </td>
        <td>
          <span class="badge ${isActHigh ? 'bg-danger' : 'bg-success'}">
            ${p.actual_waste_level} (${p.actual_waste_pct}%)
          </span>
        </td>
        <td>
          ${match ? '<span class="text-success fw-bold"><i class="bi bi-check-circle-fill"></i> Accurate</span>' : '<span class="text-danger fw-bold"><i class="bi bi-x-circle-fill"></i> Divergent</span>'}
        </td>
      </tr>
    `;
  }).join('');
}

document.addEventListener('DOMContentLoaded', loadAnalytics);
