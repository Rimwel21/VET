function updateBreeds() {
  const animal = document.getElementById('animal_type').value;
  const breeds = breedsByAnimal[animal] || [];
  const sel = document.getElementById('breed');
  sel.innerHTML = breeds.map((breed) => `<option value="${breed}">${breed}</option>`).join('');
}

function setToggle(fieldId, value, btn) {
  document.getElementById(fieldId).value = value;
  const group = btn.closest('.toggle-group');
  group.querySelectorAll('.toggle-btn').forEach((button) => {
    button.classList.remove('active-yes', 'active-no');
  });
  btn.classList.add(value === 'Yes' ? 'active-yes' : 'active-no');
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.toggle-group').forEach((group) => {
    const firstBtn = group.querySelector('.toggle-btn');
    if (firstBtn) firstBtn.classList.add('active-yes');
  });
});

const SEV_BAR = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
};

async function runPrediction() {
  const btn = document.getElementById('predict-btn');
  const errEl = document.getElementById('error-msg');
  errEl.style.display = 'none';

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Analyzing...';

  const payload = {
    animal_type: document.getElementById('animal_type').value,
    breed: document.getElementById('breed').value,
    age: document.getElementById('age').value,
    gender: document.getElementById('gender').value,
    weight: document.getElementById('weight').value,
    symptom_1: document.getElementById('symptom_1').value,
    symptom_2: document.getElementById('symptom_2').value,
    symptom_3: document.getElementById('symptom_3').value,
    symptom_4: document.getElementById('symptom_4').value,
    duration: document.getElementById('duration').value,
    appetite_loss: document.getElementById('appetite_loss').value,
    vomiting: document.getElementById('vomiting').value,
    diarrhea: document.getElementById('diarrhea').value,
    coughing: document.getElementById('coughing').value,
    labored_breathing: document.getElementById('labored_breathing').value,
    lameness: document.getElementById('lameness').value,
    skin_lesions: document.getElementById('skin_lesions').value,
    nasal_discharge: document.getElementById('nasal_discharge').value,
    eye_discharge: document.getElementById('eye_discharge').value,
    body_temperature: document.getElementById('body_temperature').value,
    heart_rate: document.getElementById('heart_rate').value,
  };

  try {
    const res = await fetch('/predict', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-CSRF-Token': window.CSRF_TOKEN
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!data.success) throw new Error(data.error || 'Prediction failed');
    renderResults(data.predictions, payload);
  } catch (error) {
    errEl.textContent = `Prediction failed: ${error.message}`;
    errEl.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon" aria-hidden="true">+</span> Predict Disease';
  }
}

function renderResults(predictions, form) {
  document.getElementById('placeholder').style.display = 'none';
  const content = document.getElementById('results-content');
  content.style.display = 'block';

  let html = `
    <div class="prediction-header">
      <span class="prediction-label">Top Predictions</span>
      <span class="prediction-count">${predictions.length} result${predictions.length > 1 ? 's' : ''}</span>
    </div>
  `;

  predictions.forEach((prediction, index) => {
    const severity = prediction.severity || 'low';
    const barColor = SEV_BAR[severity] || SEV_BAR.low;
    const rankClass = index === 0 ? 'rank-1' : '';
    const rankBadge = index === 0 ? 'pred-rank-1' : '';
    const delay = index * 80;

    html += `
      <div class="pred-card ${rankClass}" style="animation-delay:${delay}ms">
        <div class="pred-top-row">
          <div class="pred-name">${prediction.disease}</div>
          <div class="pred-rank ${rankBadge}">#${index + 1}</div>
        </div>
        <div class="conf-row">
          <div class="conf-bar-wrap">
            <div class="conf-bar" style="width:${prediction.confidence}%;background:${barColor}"></div>
          </div>
          <div class="conf-pct" style="color:${barColor}">${prediction.confidence}%</div>
        </div>
        <span class="severity-badge sev-${severity}">${severity} risk</span>
      </div>
    `;
  });

  const signs = [];
  if (form.vomiting === 'Yes') signs.push('vomiting');
  if (form.diarrhea === 'Yes') signs.push('diarrhea');
  if (form.coughing === 'Yes') signs.push('coughing');
  if (form.appetite_loss === 'Yes') signs.push('appetite loss');
  if (form.labored_breathing === 'Yes') signs.push('labored breathing');
  if (form.skin_lesions === 'Yes') signs.push('skin lesions');

  html += `
    <div class="summary-box" style="margin-top: 1.5rem; text-align: left;">
      <div style="margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid #d9e6f7;">
        <strong>${form.animal_type}</strong> / ${form.breed} / ${form.age}yr / ${form.weight}kg<br>
        Primary: <strong style="color:#1a202c;">${form.symptom_1}</strong>${signs.length ? ` / Also: ${signs.join(', ')}` : ''}
      </div>
      
      <h4 style="color: #1a3c8f; font-family: 'Nunito', sans-serif; font-size: 1rem; font-weight: 800; margin-bottom: 0.5rem;">Understanding Your Results</h4>
      <p style="margin-bottom: 0.5rem; font-size: 0.82rem; line-height: 1.5; color: #475569;">
        <strong style="color:#1a202c;">Calculation:</strong> Percentages are generated by our prediction engine based on the combination of patient features, vitals, and clinical signs matched against reference datasets.
      </p>
      <p style="margin-bottom: 0.5rem; font-size: 0.82rem; line-height: 1.5; color: #475569;">
        <strong style="color:#1a202c;">100% Normalized Scale:</strong> The top predictions are normalized to sum to 100%. This displays the relative likelihood among the most probable diseases.
      </p>
      <p style="margin-bottom: 0.5rem; font-size: 0.82rem; line-height: 1.5; color: #475569;">
        <strong style="color:#1a202c;">Risk Levels:</strong> <span style="color:#ea580c; font-weight:800;">High Risk</span> indicates potentially severe or rapid-onset conditions requiring urgent evaluation, whereas <span style="color:#16a34a; font-weight:800;">Low Risk</span> conditions may be less critical but still need monitoring.
      </p>
    </div>
    
    <div class="disclaimer" style="margin-top: 1rem; padding: 0.85rem; background: #fee2e2; border: 1px solid #fca5a5; color: #991b1b; border-radius: 12px; font-weight: 700; font-size: 0.8rem; text-align: left; display: flex; gap: 0.5rem; align-items: flex-start;">
      <span style="font-size: 1.2rem; line-height: 1;">⚠️</span>
      <span><strong>Veterinary Reference Only:</strong> These automated predictions are strictly for informational and reference purposes. They do not constitute a clinical diagnosis and must always be validated by a licensed veterinarian.</span>
    </div>
  `;

  content.innerHTML = html;
}
