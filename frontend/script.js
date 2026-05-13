const fileInput = document.getElementById('fileInput');
const uploadBox = document.getElementById('uploadBox');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const clearBtn = document.getElementById('clearBtn');
const extractBtn = document.getElementById('extractBtn');
const loader = document.getElementById('loader');
const results = document.getElementById('results');

let selectedFile = null;

// Click upload box to browse
uploadBox.addEventListener('click', () => fileInput.click());

// File selected
fileInput.addEventListener('change', (e) => {
  handleFile(e.target.files[0]);
});

// Drag and drop
uploadBox.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadBox.classList.add('dragover');
});

uploadBox.addEventListener('dragleave', () => {
  uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadBox.classList.remove('dragover');
  handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
  if (!file) return;
  selectedFile = file;
  fileName.textContent = file.name;
  fileInfo.style.display = 'flex';
  extractBtn.disabled = false;
  results.style.display = 'none';
}

// Clear file
clearBtn.addEventListener('click', () => {
  selectedFile = null;
  fileInput.value = '';
  fileInfo.style.display = 'none';
  extractBtn.disabled = true;
  results.style.display = 'none';
});

// Extract
extractBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  loader.style.display = 'block';
  results.style.display = 'none';
  extractBtn.disabled = true;

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const response = await fetch('http://127.0.0.1:8000/extract', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();
    displayResults(data.extraction);

  } catch (error) {
    alert('Error connecting to backend. Make sure it is running.');
  } finally {
    loader.style.display = 'none';
    extractBtn.disabled = false;
  }
});

function displayResults(data) {

  window.lastExtractionData = data;
  // Doc type badge
  document.getElementById('docType').textContent = data.document_type || 'unknown';

  // Confidence
  const conf = data.confidence || 'medium';
  document.getElementById('confidence').textContent = `${conf} confidence`;

  // Summary
  document.getElementById('summary').textContent = data.summary || 'No summary available.';

  // Key fields
  const keyFieldsDiv = document.getElementById('keyFields');
  keyFieldsDiv.innerHTML = '';

  if (data.key_fields) {
    renderFields(data.key_fields, keyFieldsDiv);
  }
 
  // Anomalies
  const anomalyCard = document.getElementById('anomalyCard');
  const anomalyList = document.getElementById('anomalies');
  anomalyList.innerHTML = '';

  if (data.anomalies && data.anomalies.length > 0) {
    data.anomalies.forEach(a => {
      const li = document.createElement('li');
      li.textContent = a;
      anomalyList.appendChild(li);
    });
    anomalyCard.style.display = 'block';
  } else {
    anomalyCard.style.display = 'none';
  }

  results.style.display = 'block';
  results.scrollIntoView({ behavior: 'smooth' });
  // Show export buttons
  document.getElementById('exportButtons').style.display = 'flex';  
}

function renderFields(obj, container, depth = 0) {
  for (const [key, value] of Object.entries(obj)) {
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      const subTitle = document.createElement('p');
      subTitle.style.cssText = 'color:#666; font-size:0.8rem; margin: 12px 0 6px; text-transform:uppercase;';
      subTitle.textContent = key;
      container.appendChild(subTitle);
      renderFields(value, container, depth + 1);
    } else {
      const row = document.createElement('div');
      row.className = 'key-field';
      const displayValue = Array.isArray(value) ? value.join(', ') : value;
      row.innerHTML = `
        <span class="label">${key.replace(/_/g, ' ')}</span>
        <span class="value">${displayValue}</span>
      `;
      container.appendChild(row);
    }
  }
}
document.getElementById('exportExcel').addEventListener('click', () => {
  if (!window.lastExtractionData) return;

  const data = window.lastExtractionData;
  const rows = [];

  // Header info
  rows.push(['DocuAgent Extraction Report']);
  rows.push(['Document Type', data.document_type || '']);
  rows.push(['Confidence', data.confidence || '']);
  rows.push(['Summary', data.summary || '']);
  rows.push([]);
  rows.push(['Field', 'Value']);

  // Flatten key fields
  function flattenFields(obj, prefix = '') {
    for (const [key, value] of Object.entries(obj)) {
      const label = (prefix + key).replace(/_/g, ' ');
      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        flattenFields(value, label + ' > ');
      } else if (Array.isArray(value)) {
        rows.push([label, value.join(', ')]);
      } else {
        rows.push([label, value]);
      }
    }
  }

  if (data.key_fields) flattenFields(data.key_fields);

  // Anomalies
  if (data.anomalies && data.anomalies.length > 0) {
    rows.push([]);
    rows.push(['Anomalies']);
    data.anomalies.forEach(a => rows.push(['', a]));
  }

  // Build workbook
  const ws = XLSX.utils.aoa_to_sheet(rows);

  // Column widths
  ws['!cols'] = [{ wch: 30 }, { wch: 80 }];

  // Style header row
  ws['A1'].s = { font: { bold: true, sz: 14 } };

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Extraction');

  XLSX.writeFile(wb, 'DocuAgent_Extraction.xlsx');
});

document.getElementById('exportPdf').addEventListener('click', async () => {
  const response = await fetch('http://127.0.0.1:8000/export/pdf');
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'docuagent_report.pdf';
  a.click();
});