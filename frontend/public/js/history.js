// Meal History & CRUD Operations Controller

let currentPage = 1;
let currentLimit = 15;
let currentMealToEdit = null;
let currentMealToDeleteId = null;

async function loadMealHistory(page = 1) {
  currentPage = page;
  const search = document.getElementById('filter-search').value.trim();
  const mealType = document.getElementById('filter-meal-type').value;
  const wasteLevel = document.getElementById('filter-waste-level').value;
  const startDate = document.getElementById('filter-start-date').value;
  const endDate = document.getElementById('filter-end-date').value;
  const sortBy = document.getElementById('filter-sort-by').value;

  const tbody = document.getElementById('history-tbody');
  tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading meal records...</td></tr>';

  try {
    const query = new URLSearchParams({
      page: currentPage,
      limit: currentLimit,
      search: search,
      meal_type: mealType,
      waste_level: wasteLevel,
      start_date: startDate,
      end_date: endDate,
      sort_by: sortBy,
      sort_order: -1
    });

    const data = await API.get(`/meals?${query.toString()}`);
    renderMealTable(data);
    renderPagination(data);
  } catch (err) {
    console.error('Error loading history:', err);
    tbody.innerHTML = '<tr><td colspan="10" class="text-center text-danger py-4">Error loading records from MongoDB.</td></tr>';
    showToast('Error', 'Failed to retrieve meal records.', 'danger');
  }
}

function renderMealTable(data) {
  const tbody = document.getElementById('history-tbody');
  const records = data.records || [];
  document.getElementById('total-records-count').textContent = (data.total_records || 0).toLocaleString();

  if (records.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="text-center py-5 text-muted">No matching meal records found in MongoDB.</td></tr>';
    return;
  }

  tbody.innerHTML = records.map(meal => {
    const isHigh = meal.waste_level === 'HIGH';
    const badge = isHigh
      ? `<span class="badge-high-waste"><i class="bi bi-exclamation-triangle-fill"></i> HIGH (${meal.waste_percentage}%)</span>`
      : `<span class="badge-low-waste"><i class="bi bi-check-circle-fill"></i> LOW (${meal.waste_percentage}%)</span>`;

    const menu = Array.isArray(meal.menu_items) ? meal.menu_items.join(', ') : (meal.menu_items || 'Meal');

    return `
      <tr>
        <td><strong>${meal.date}</strong></td>
        <td><span class="badge bg-secondary">${meal.meal_type}</span></td>
        <td>
          <div class="fw-semibold text-dark">${menu}</div>
          <small class="text-muted">${meal.food_category || 'General'} &bull; ${meal.menu_complexity || 'Moderate'}</small>
        </td>
        <td>${meal.expected_students || '--'}</td>
        <td><strong>${meal.actual_attendance || '--'}</strong></td>
        <td>${meal.food_prepared_kg} kg</td>
        <td>${meal.food_consumed_kg} kg</td>
        <td>${meal.leftover_food_kg} kg</td>
        <td>${badge}</td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-primary" onclick="openEditModal('${meal.id}')" title="Edit Record">
              <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-outline-danger" onclick="openDeleteModal('${meal.id}')" title="Delete Record">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderPagination(data) {
  const container = document.getElementById('pagination-container');
  const totalPages = data.total_pages || 1;
  const current = data.current_page || 1;

  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }

  let html = `<ul class="pagination pagination-sm mb-0">`;
  html += `
    <li class="page-item ${current === 1 ? 'disabled' : ''}">
      <button class="page-link" onclick="loadMealHistory(${current - 1})">&laquo; Prev</button>
    </li>
  `;

  const startPage = Math.max(1, current - 2);
  const endPage = Math.min(totalPages, current + 2);

  for (let p = startPage; p <= endPage; p++) {
    html += `
      <li class="page-item ${p === current ? 'active' : ''}">
        <button class="page-link" onclick="loadMealHistory(${p})">${p}</button>
      </li>
    `;
  }

  html += `
    <li class="page-item ${current === totalPages ? 'disabled' : ''}">
      <button class="page-link" onclick="loadMealHistory(${current + 1})">Next &raquo;</button>
    </li>
  `;
  html += `</ul>`;
  container.innerHTML = html;
}

// Edit Modal Handling
async function openEditModal(mealId) {
  try {
    const meal = await API.get(`/meals/${mealId}`);
    currentMealToEdit = meal;

    document.getElementById('edit-meal-id').value = meal.id;
    document.getElementById('edit-date').value = meal.date;
    document.getElementById('edit-meal-type').value = meal.meal_type;
    document.getElementById('edit-menu-items').value = Array.isArray(meal.menu_items) ? meal.menu_items.join(', ') : meal.menu_items;
    document.getElementById('edit-actual-attendance').value = meal.actual_attendance;
    document.getElementById('edit-food-prepared').value = meal.food_prepared_kg;
    document.getElementById('edit-food-consumed').value = meal.food_consumed_kg;
    document.getElementById('edit-leftover-food').value = meal.leftover_food_kg;

    const modal = new bootstrap.Modal(document.getElementById('editMealModal'));
    modal.show();
  } catch (err) {
    console.error('Error fetching meal for edit:', err);
    showToast('Error', 'Could not open meal record.', 'danger');
  }
}

async function handleSaveEdit() {
  const mealId = document.getElementById('edit-meal-id').value;
  const payload = {
    date: document.getElementById('edit-date').value,
    meal_type: document.getElementById('edit-meal-type').value,
    menu_items: document.getElementById('edit-menu-items').value.split(',').map(s => s.trim()).filter(Boolean),
    actual_attendance: parseInt(document.getElementById('edit-actual-attendance').value, 10),
    food_prepared_kg: parseFloat(document.getElementById('edit-food-prepared').value),
    food_consumed_kg: parseFloat(document.getElementById('edit-food-consumed').value),
    leftover_food_kg: parseFloat(document.getElementById('edit-leftover-food').value)
  };

  try {
    await API.put(`/meals/${mealId}`, payload);
    showToast('Success', 'Meal record updated successfully in MongoDB.', 'success');
    bootstrap.Modal.getInstance(document.getElementById('editMealModal')).hide();
    loadMealHistory(currentPage);
  } catch (err) {
    console.error('Error updating meal:', err);
    showToast('Update Failed', err.message || 'Could not update record.', 'danger');
  }
}

// Delete Modal Handling
function openDeleteModal(mealId) {
  currentMealToDeleteId = mealId;
  const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
  modal.show();
}

async function confirmDeleteMeal() {
  if (!currentMealToDeleteId) return;

  try {
    await API.delete(`/meals/${currentMealToDeleteId}`);
    showToast('Deleted', 'Meal record deleted from MongoDB.', 'success');
    bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal')).hide();
    loadMealHistory(currentPage);
  } catch (err) {
    console.error('Error deleting meal:', err);
    showToast('Delete Failed', err.message || 'Could not delete meal.', 'danger');
  }
}

// Reset Filters
function resetFilters() {
  document.getElementById('filter-search').value = '';
  document.getElementById('filter-meal-type').value = '';
  document.getElementById('filter-waste-level').value = '';
  document.getElementById('filter-start-date').value = '';
  document.getElementById('filter-end-date').value = '';
  document.getElementById('filter-sort-by').value = 'date';
  loadMealHistory(1);
}

document.addEventListener('DOMContentLoaded', () => {
  loadMealHistory(1);

  // Bind filter triggers
  document.getElementById('filter-search').addEventListener('input', () => loadMealHistory(1));
  document.getElementById('filter-meal-type').addEventListener('change', () => loadMealHistory(1));
  document.getElementById('filter-waste-level').addEventListener('change', () => loadMealHistory(1));
  document.getElementById('filter-start-date').addEventListener('change', () => loadMealHistory(1));
  document.getElementById('filter-end-date').addEventListener('change', () => loadMealHistory(1));
  document.getElementById('filter-sort-by').addEventListener('change', () => loadMealHistory(1));

  // Edit form live leftover calculation
  const prep = document.getElementById('edit-food-prepared');
  const cons = document.getElementById('edit-food-consumed');
  const left = document.getElementById('edit-leftover-food');
  const calcEdit = () => {
    const p = parseFloat(prep.value) || 0;
    const c = parseFloat(cons.value) || 0;
    left.value = Math.max(0, p - c).toFixed(1);
  };
  prep.addEventListener('input', calcEdit);
  cons.addEventListener('input', calcEdit);
});
