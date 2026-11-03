// Food Waste Prediction Page Controller

let foodCatalog = [];

async function initPredictPage() {
  // Set default date to today
  const dateInput = document.getElementById('pred-date');
  if (dateInput && !dateInput.value) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }

  // Load food catalogue for autocomplete / chip selection
  try {
    const data = await API.get('/foods');
    foodCatalog = data.foods || [];
    renderFoodChips(foodCatalog);
    populateCategoryDropdown(data.categories || []);
  } catch (err) {
    console.error('Error fetching food items:', err);
  }

  // Sync temperature slider and number
  const tempSlider = document.getElementById('pred-temp-slider');
  const tempInput = document.getElementById('pred-temperature');
  if (tempSlider && tempInput) {
    tempSlider.addEventListener('input', (e) => { tempInput.value = e.target.value; });
    tempInput.addEventListener('input', (e) => { tempSlider.value = e.target.value; });
  }

  // Handle Form Submission
  const form = document.getElementById('prediction-form');
  if (form) {
    form.addEventListener('submit', handlePredictionSubmit);
  }
}

function renderFoodChips(foods) {
  const container = document.getElementById('food-chips-container');
  if (!container) return;

  const currentMealType = document.getElementById('pred-meal-type').value;
  const filtered = foods.filter(f => f.meal_types.includes(currentMealType));

  container.innerHTML = filtered.map(f => `
    <span class="food-chip" onclick="selectFoodItem('${f.name}', '${f.category}', '${f.complexity}')">
      ${f.name}
    </span>
  `).join('');
}

function filterChipsByMealType() {
  if (foodCatalog.length > 0) {
    renderFoodChips(foodCatalog);
  }
}

function selectFoodItem(name, category, complexity) {
  document.getElementById('pred-menu-items').value = name;
  if (category) {
    document.getElementById('pred-food-category').value = category;
  }
  if (complexity) {
    document.getElementById('pred-menu-complexity').value = complexity;
  }
}

function populateCategoryDropdown(categories) {
  const select = document.getElementById('pred-food-category');
  if (!select) return;

  const current = select.value;
  select.innerHTML = '<option value="">-- Select Food Category --</option>' +
    categories.map(c => `<option value="${c}" ${c === current ? 'selected' : ''}>${c}</option>`).join('');
}

async function handlePredictionSubmit(e) {
  e.preventDefault();

  const submitBtn = document.getElementById('btn-submit-predict');
  const originalBtnText = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Analyzing Historical Data & Predicting...';

  const payload = {
    date: document.getElementById('pred-date').value,
    meal_type: document.getElementById('pred-meal-type').value,
    food_category: document.getElementById('pred-food-category').value,
    menu_items: document.getElementById('pred-menu-items').value.split(',').map(s => s.trim()).filter(Boolean),
    expected_students: parseInt(document.getElementById('pred-expected-students').value, 10),
    total_hostel_population: parseInt(document.getElementById('pred-total-population').value, 10),
    is_holiday_or_event: document.getElementById('pred-is-holiday').checked,
    event_details: document.getElementById('pred-event-details').value.trim() || 'None',
    weather: document.getElementById('pred-weather').value,
    temperature: parseFloat(document.getElementById('pred-temperature').value),
    menu_complexity: document.getElementById('pred-menu-complexity').value
  };

  try {
    const result = await API.post('/predict', payload);
    renderPredictionResults(result, payload);
    showToast('Prediction Complete', `Predicted: ${result.prediction} (${result.probability_high_waste}% risk)`, result.prediction === 'HIGH WASTE' ? 'warning' : 'success');
  } catch (err) {
    console.error('Prediction failed:', err);
    showToast('Prediction Failed', err.message || 'An error occurred during prediction.', 'danger');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnText;
  }
}

function renderPredictionResults(res, payload) {
  const resultsContainer = document.getElementById('prediction-results-card');
  resultsContainer.classList.remove('d-none');
  resultsContainer.scrollIntoView({ behavior: 'smooth' });

  const isHigh = res.prediction === 'HIGH WASTE';
  const probHigh = res.probability_high_waste;
  const probLow = res.probability_low_waste;

  // Banner & Risk
  const resultBanner = document.getElementById('result-prediction-banner');
  const riskBox = document.getElementById('result-box-container');

  if (isHigh) {
    resultBanner.innerHTML = `
      <div class="alert alert-danger d-flex align-items-center mb-0">
        <i class="bi bi-exclamation-octagon-fill fs-3 me-3 text-danger"></i>
        <div>
          <h4 class="alert-heading fw-bold mb-1">HIGH FOOD WASTE PREDICTED</h4>
          <p class="mb-0">The model predicts significant leftover risk for this meal (${probHigh}% probability of exceeding the 15% threshold).</p>
        </div>
      </div>
    `;
    riskBox.className = 'prediction-box high-risk mt-3';
  } else {
    resultBanner.innerHTML = `
      <div class="alert alert-success d-flex align-items-center mb-0">
        <i class="bi bi-check-circle-fill fs-3 me-3 text-success"></i>
        <div>
          <h4 class="alert-heading fw-bold mb-1">LOW FOOD WASTE PREDICTED</h4>
          <p class="mb-0">Meal is on track for optimal consumption (${probLow}% probability of remaining under the 15% threshold).</p>
        </div>
      </div>
    `;
    riskBox.className = 'prediction-box low-risk mt-3';
  }

  // Probability Meter
  const probBar = document.getElementById('result-prob-bar');
  probBar.style.width = `${probHigh}%`;
  probBar.className = `progress-bar ${isHigh ? 'bg-danger' : 'bg-success'}`;
  document.getElementById('result-prob-high-val').textContent = `${probHigh}%`;
  document.getElementById('result-prob-low-val').textContent = `${probLow}%`;
  document.getElementById('result-risk-level').textContent = res.risk_level;
  document.getElementById('result-risk-level').className = `badge bg-${res.risk_badge_class} fs-6 px-3 py-2`;

  // Recommended Prep Quantity
  document.getElementById('result-recommended-kg').textContent = `${res.recommended_food_prep_kg} kg`;

  // Suggestions List
  const suggestionsList = document.getElementById('result-suggestions-list');
  if (res.suggestions && res.suggestions.length > 0) {
    suggestionsList.innerHTML = res.suggestions.map(s => `
      <div class="p-3 mb-2 rounded border bg-white border-${s.type} d-flex align-items-start gap-3">
        <i class="bi ${s.type === 'danger' ? 'bi-exclamation-triangle-fill text-danger' : s.type === 'warning' ? 'bi-shield-exclamation text-warning' : 'bi-lightbulb-fill text-primary'} fs-4 mt-1"></i>
        <div>
          <h6 class="fw-bold mb-1 text-${s.type}">${s.title}</h6>
          <p class="mb-0 small text-dark">${s.text}</p>
        </div>
      </div>
    `).join('');
  } else {
    suggestionsList.innerHTML = '<p class="text-muted">Standard kitchen preparation protocols apply.</p>';
  }

  // Historical Analysis Section (Strictly prior records)
  const hist = res.historical_analysis;
  const histContainer = document.getElementById('result-historical-analysis');

  if (hist.has_sufficient_history) {
    histContainer.innerHTML = `
      <div class="p-3 bg-light rounded border">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="badge bg-success"><i class="bi bi-shield-check me-1"></i> Historical Analysis Complete</span>
          <span class="text-muted small">Based on <strong>${hist.total_prior_records}</strong> prior meals before ${payload.date}</span>
        </div>
        <div class="row g-2 text-center mt-2">
          <div class="col-6 col-md-3">
            <div class="bg-white p-2 rounded border">
              <small class="text-muted d-block">${payload.meal_type} Prior Avg</small>
              <strong class="fs-6">${hist.meal_avg_waste}%</strong>
            </div>
          </div>
          <div class="col-6 col-md-3">
            <div class="bg-white p-2 rounded border">
              <small class="text-muted d-block">${payload.food_category} Avg</small>
              <strong class="fs-6">${hist.category_avg_waste}%</strong>
            </div>
          </div>
          <div class="col-6 col-md-3">
            <div class="bg-white p-2 rounded border">
              <small class="text-muted d-block">Dish Prior Avg</small>
              <strong class="fs-6">${hist.menu_items_avg_waste}%</strong>
            </div>
          </div>
          <div class="col-6 col-md-3">
            <div class="bg-white p-2 rounded border">
              <small class="text-muted d-block">${hist.target_weekday} Avg</small>
              <strong class="fs-6">${hist.weekday_avg_waste}%</strong>
            </div>
          </div>
        </div>
        <div class="mt-2 text-muted small text-center">
          <i class="bi bi-info-circle me-1"></i> ${hist.message}
        </div>
      </div>
    `;
  } else {
    histContainer.innerHTML = `
      <div class="alert alert-warning mb-0">
        <i class="bi bi-info-triangle-fill me-2"></i>
        <strong>Notice on Historical Data:</strong> ${hist.message}
      </div>
    `;
  }
}

document.addEventListener('DOMContentLoaded', initPredictPage);
