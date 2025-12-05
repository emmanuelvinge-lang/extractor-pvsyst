const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const loading = document.getElementById('loading');
const resultArea = document.getElementById('result-area');
const downloadBtn = document.getElementById('download-btn');
const dataTableBody = document.querySelector('#data-table tbody');
const resetBtn = document.getElementById('reset-btn');

// Drag & Drop events
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleFiles(Array.from(e.dataTransfer.files));
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
        handleFiles(Array.from(fileInput.files));
    }
});

resetBtn.addEventListener('click', () => {
    resultArea.classList.add('hidden');
    dropZone.classList.remove('hidden');
    fileInput.value = '';
});

async function handleFiles(files) {
    // Validar que todos sean PDFs
    const invalidFiles = files.filter(f => f.type !== 'application/pdf');
    if (invalidFiles.length > 0) {
        alert('Por favor sube solo archivos PDF.');
        return;
    }

    // Show loading
    dropZone.classList.add('hidden');
    loading.classList.remove('hidden');
    loading.querySelector('p').textContent = `Procesando ${files.length} archivo(s)...`;

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Error al procesar los archivos');
        }

        displayResults(result);

    } catch (error) {
        alert(error.message);
        dropZone.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
    }
}

function displayResults(result) {
    // Update download link
    downloadBtn.href = result.download_url;

    // Populate table with all rows
    dataTableBody.innerHTML = '';
    const allData = result.data;

    // Helper function to safely convert values to string
    const safeStringify = (value) => {
        if (value === null || value === undefined) return 'N/A';
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    };

    if (allData.length === 0) {
        dataTableBody.innerHTML = '<tr><td colspan="2">No se extrajeron datos</td></tr>';
    } else {
        // Get all unique keys from all data objects
        const allKeys = [...new Set(allData.flatMap(obj => Object.keys(obj)))];

        // Create header row with file names
        const headerRow = document.createElement('tr');
        headerRow.innerHTML = '<th>Campo</th>' + allData.map((d, i) =>
            `<th>${safeStringify(d['Nombre del Archivo']) || `Archivo ${i + 1}`}</th>`
        ).join('');
        dataTableBody.parentElement.querySelector('thead tr').innerHTML = headerRow.innerHTML;

        // Create data rows
        allKeys.forEach(key => {
            if (key === 'Nombre del Archivo') return; // Skip filename in body

            const row = document.createElement('tr');
            row.innerHTML = `<td><strong>${key}</strong></td>` +
                allData.map(d => `<td>${safeStringify(d[key])}</td>`).join('');
            dataTableBody.appendChild(row);
        });
    }

    // Show results
    resultArea.classList.remove('hidden');
}
