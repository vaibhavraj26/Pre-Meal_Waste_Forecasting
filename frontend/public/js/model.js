// Model Performance & Retraining Controller

let featureChart = null;

async function loadModelPerformance() {
  try {
    const data = await API.get('/ml/performance');
    const metrics = data.metrics || {};
    renderMetrics(metrics);
    renderConfusionMatrix(metrics.confusion_matrix || {});
    renderFeatureImportanceChart(metrics.top_risk_factors || []);
    renderTrainingHistory(data.training_history || []);
    setupRetrainButton(data);
  } catch (err) {
    console.error('Error loading model metrics:', err);
    showToast('ML Metrics Error', 'Could not load model performance summary.', 'danger');
  }
}

function renderMetrics(m) {
  document.getElementById('metric-accuracy').textContent = (m.accuracy || 0) + '%';
  document.getElementById('metric-precision').textContent = (m.precision || 0) + '%';
  document.getElementById('metric-recall').textContent = (m.recall || 0) + '%';
  document.getElementById('metric-f1').textContent = (m.f1_score || 0) + '%';
  document.getElementById('metric-roc-auc').textContent = (m.roc_auc || 0) + '%';

  document.getElementById('meta-last-trained').textContent = m.last_trained ? new Date(m.last_trained).toLocaleString() : 'N/A';
  document.getElementById('meta-total-samples').textContent = (m.total_records_trained || 0).toLocaleString();
  document.getElementById('meta-train-samples').textContent = (m.train_samples || 0).toLocaleString();
  document.getElementById('meta-test-samples').textContent = (m.test_samples || 0).toLocaleString();
}

function renderConfusionMatrix(cm) {
  const tn = cm.true_negatives || 0;
  const fp = cm.false_positives || 0;
  const fn = cm.false_negatives || 0;
  const tp = cm.true_positives || 0;

  document.getElementById('cm-tn').textContent = tn;
  document.getElementById('cm-fp').textContent = fp;
  document.getElementById('cm-fn').textContent = fn;
  document.getElementById('cm-tp').textContent = tp;

  const total = tn + fp + fn + tp;
  const correct = tn + tp;
  const correctPct = total > 0 ? Math.round((correct / total) * 100) : 0;

  document.getElementById('cm-summary-text').textContent =
    `Out of ${total} test meals, the model correctly classified ${correct} (${correctPct}%), with ${fp} false alarms and ${fn} missed high-waste events.`;
}

function renderFeatureImportanceChart(factors) {
  const ctx = document.getElementById('featureImportanceChart');
  if (!ctx) return;

  const labels = factors.map(f => f.feature.replace(/_/g, ' '));
  const data = factors.map(f => f.weight);
  const colors = data.map(w => w > 0 ? '#ef4444' : '#10b981');

  if (featureChart) featureChart.destroy();

  featureChart = new Chart(ctx, {
    type: 'bar',
    indexAxis: 'y',
    data: {
      labels: labels,
      datasets: [{
        label: 'Regression Coefficient (Red = Increases Waste, Green = Decreases Waste)',
        data: data,
        backgroundColor: colors,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: { display: true, text: 'Log-Odds Coefficient Weight' }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(ctx) {
              const val = ctx.parsed.x;
              return val > 0
                ? `Increases High Waste Risk (+${val})`
                : `Decreases High Waste Risk (${val})`;
            }
          }
        }
      }
    }
  });
}

function renderTrainingHistory(history) {
  const tbody = document.getElementById('training-history-tbody');
  if (!tbody) return;

  if (history.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">No historical training sessions logged yet.</td></tr>';
    return;
  }

  tbody.innerHTML = history.map((h, idx) => `
    <tr>
      <td><strong>#${history.length - idx}</strong></td>
      <td>${new Date(h.timestamp).toLocaleString()}</td>
      <td>${h.total_records || '--'}</td>
      <td><span class="badge bg-primary">${h.accuracy}%</span></td>
      <td>${h.precision}%</td>
      <td>${h.recall}%</td>
      <td><strong>${h.f1_score}%</strong></td>
    </tr>
  `).join('');
}

function setupRetrainButton(data) {
  const btn = document.getElementById('btn-retrain-model');
  const alertBox = document.getElementById('retrain-status-text');

  if (!btn) return;

  if (data.can_retrain) {
    btn.disabled = false;
    alertBox.className = 'text-success small';
    alertBox.innerHTML = `<i class="bi bi-check-circle me-1"></i> Ready: ${data.total_available_meals} meal records available in MongoDB (minimum required: ${data.min_retrain_threshold}).`;
  } else {
    btn.disabled = true;
    alertBox.className = 'text-warning small';
    alertBox.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i> Retraining requires at least ${data.min_retrain_threshold} meal records. Current count: ${data.total_available_meals}.`;
  }

  btn.onclick = async () => {
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Retraining Logistic Regression Model...';

    try {
      const res = await API.post('/ml/retrain', {});
      showToast('Model Retrained', `Model successfully retrained! New Accuracy: ${res.metrics.accuracy}%`, 'success');
      await loadModelPerformance();
    } catch (err) {
      console.error('Error retraining model:', err);
      showToast('Retrain Failed', err.message || 'Could not retrain model.', 'danger');
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  };
}

document.addEventListener('DOMContentLoaded', loadModelPerformance);
