// Add Meal Record Page Controller

let foodCatalog = [];

async function initAddMealPage() {
  const dateInput = document.getElementById('meal-date');
  if (dateInput && !dateInput.value) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }

  // Load foods for quick auto-fill
  try {
    const data = await API.get('/foods');
    foodCatalog = data.foods || [];
    renderAddMealChips(foodCatalog);
  } catch (err) {
    console.error('Error fetching food catalog:', err);
  }

  // Bind live calculation listeners
  const preparedInput = document.getElementById('meal-food-prepared');
  const consumedInput = document.getElementById('meal-food-consumed');
  const leftoverInput = document.getElementById('meal-food-leftover');

  preparedInput.addEventListener('input', calculateWasteLive);
  consumedInput.addEventListener('input', calculateWasteLive);
  leftoverInput.addEventListener('input', calculateWasteLiveManualLeftover);

  // Form submit
  const form = document.getElementById('add-meal-form');
  if (form) {
    form.addEventListener('submit', handleAddMealSubmit);
  }
}

function renderAddMealChips(foods) {
  const container = document.getElementById('add-food-chips');
  if (!container) return;

  const currentMeal = document.getElementById('meal-type').value;
  const filtered = foods.filter(f => f.meal_types.includes(currentMeal));

  container.innerHTML = filtered.map(f => `
    <span class="food-chip" onclick="selectAddMealFood('${f.name}', '${f.category}', '${f.complexity}')">
      ${f.name}
    </span>
  `).join('');
}

function filterAddMealChips() {
  if (foodCatalog.length > 0) {
    renderAddMealChips(foodCatalog);
  }
}

function selectAddMealFood(name, category, complexity) {
  document.getElementById('meal-menu-items').value = name;
  if (category) {
    document.getElementById('meal-food-category').value = category;
  }
  if (complexity) {
    document.getElementById('meal-menu-complexity').value = complexity;
  }
}

function calculateWasteLive() {
  const prepared = parseFloat(document.getElementById('meal-food-prepared').value) || 0;
  const consumed = parseFloat(document.getElementById('meal-food-consumed').value) || 0;

  const leftover = Math.max(0, prepared - consumed);
  document.getElementById('meal-food-leftover').value = leftover.toFixed(1);

  updateWasteBadge(prepared, leftover);
}

function calculateWasteLiveManualLeftover() {
  const prepared = parseFloat(document.getElementById('meal-food-prepared').value) || 0;
  const leftover = parseFloat(document.getElementById('meal-food-leftover').value) || 0;

  updateWasteBadge(prepared, leftover);
}

function updateWasteBadge(prepared, leftover) {
  let wastePct = 0;
  if (prepared > 0) {
    wastePct = Math.round((leftover / prepared) * 1000) / 10;
  }

  const wastePctEl = document.getElementById('preview-waste-pct');
  const wasteBadgeEl = document.getElementById('preview-waste-badge');

  wastePctEl.textContent = `${wastePct}%`;

  if (wastePct > 15.0) {
    wasteBadgeEl.className = 'badge bg-danger fs-6 px-3 py-2';
    wasteBadgeEl.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-1"></i> HIGH WASTE (>15%)';
  } else {
    wasteBadgeEl.className = 'badge bg-success fs-6 px-3 py-2';
    wasteBadgeEl.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> LOW WASTE (&le;15%)';
  }
}

async function handleAddMealSubmit(e) {
  e.preventDefault();

  const submitBtn = document.getElementById('btn-save-meal');
  const origText = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Saving to MongoDB...';

  const payload = {
    date: document.getElementById('meal-date').value,
    meal_type: document.getElementById('meal-type').value,
    menu_items: document.getElementById('meal-menu-items').value.split(',').map(s => s.trim()).filter(Boolean),
    food_category: document.getElementById('meal-food-category').value,
    menu_complexity: document.getElementById('meal-menu-complexity').value,
    expected_students: parseInt(document.getElementById('meal-expected-students').value, 10),
    actual_attendance: parseInt(document.getElementById('meal-actual-attendance').value, 10),
    total_hostel_population: parseInt(document.getElementById('meal-total-population').value, 10),
    food_prepared_kg: parseFloat(document.getElementById('meal-food-prepared').value),
    food_consumed_kg: parseFloat(document.getElementById('meal-food-consumed').value),
    leftover_food_kg: parseFloat(document.getElementById('meal-food-leftover').value),
    weather: document.getElementById('meal-weather').value,
    temperature: parseFloat(document.getElementById('meal-temperature').value),
    is_holiday_or_event: document.getElementById('meal-is-holiday').checked,
    event_details: document.getElementById('meal-event-details').value.trim() || 'None'
  };

  try {
    const res = await API.post('/meals', payload);
    showToast('Success', 'Meal record successfully saved in MongoDB!', 'success');

    // Show Success Modal / Banner
    document.getElementById('add-meal-form').reset();
    document.getElementById('meal-date').value = new Date().toISOString().split('T')[0];
    calculateWasteLive();

    const banner = document.getElementById('save-success-banner');
    if (banner) {
      banner.classList.remove('d-none');
      banner.scrollIntoView({ behavior: 'smooth' });
    }
  } catch (err) {
    console.error('Error saving meal:', err);
    showToast('Save Failed', err.message || 'Could not save record to database.', 'danger');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = origText;
  }
}

document.addEventListener('DOMContentLoaded', initAddMealPage);
