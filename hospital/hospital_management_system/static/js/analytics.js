(function () {
    const page = document.querySelector('[data-analytics-page]');
    if (!page) return;
    if (typeof Chart === 'undefined') {
        const status = document.querySelector('[data-analytics-status]');
        if (status) status.textContent = 'Charts could not be loaded. Check your connection and refresh the page.';
        return;
    }

    const startInput = document.getElementById('analyticsStart');
    const endInput = document.getElementById('analyticsEnd');
    const departmentInput = document.getElementById('analyticsDepartment');
    const applyButton = document.querySelector('[data-analytics-apply]');
    const status = document.querySelector('[data-analytics-status]');
    const charts = {};
    const chartColors = ['#1769aa', '#0b8f87', '#e28b3d', '#d45b70', '#7057a7', '#647b8d', '#2eaa73'];

    function localDate(daysAgo) {
        const value = new Date();
        value.setDate(value.getDate() - daysAgo);
        return value.toISOString().slice(0, 10);
    }

    startInput.value = localDate(365);
    endInput.value = localDate(0);
    startInput.max = endInput.value;
    endInput.max = endInput.value;

    function formatNumber(value) { return new Intl.NumberFormat('en-US').format(value || 0); }
    function formatMoney(value) { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value || 0); }
    function setMetric(name, value) { const element = document.querySelector(`[data-metric="${name}"]`); if (element) element.textContent = ['revenue', 'pending_payments'].includes(name) ? formatMoney(value) : formatNumber(value); }

    function renderChart(id, type, labels, values, label, options) {
        const canvas = document.getElementById(id);
        const panel = canvas.closest('.chart-panel');
        const hasData = values.some(value => Number(value) > 0);
        panel.classList.toggle('is-empty', !hasData);
        if (charts[id]) charts[id].destroy();
        if (!hasData) return;
        charts[id] = new Chart(canvas, { type, data: { labels, datasets: [{ label, data: values, borderColor: '#1769aa', backgroundColor: type === 'doughnut' ? chartColors : 'rgba(23, 105, 170, .14)', borderWidth: type === 'doughnut' ? 2 : 2, fill: type !== 'doughnut', tension: .35, borderRadius: type === 'bar' ? 5 : 0 }] }, options: Object.assign({ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: type === 'doughnut', position: 'bottom', labels: { usePointStyle: true, padding: 16 } }, tooltip: { callbacks: { label: context => `${context.dataset.label}: ${type === 'doughnut' ? formatNumber(context.raw) : formatNumber(context.raw)}` } } }, scales: type === 'doughnut' ? {} : { y: { beginAtZero: true, grid: { color: '#edf2f4' }, ticks: { precision: 0 } }, x: { grid: { display: false } } } }, options || {}) });
    }

    function updateDashboard(data) {
        Object.entries(data.cards).forEach(([key, value]) => setMetric(key, value));
        const chartData = data.charts;
        renderChart('patientsChart', 'line', chartData.labels, chartData.patients_per_month, 'Patients');
        renderChart('appointmentsChart', 'bar', chartData.labels, chartData.appointments_per_month, 'Appointments');
        renderChart('revenueChart', 'line', chartData.labels, chartData.revenue_per_month, 'Revenue');
        renderChart('departmentChart', 'doughnut', chartData.department_patients.labels, chartData.department_patients.values, 'Patients');
        renderChart('statusChart', 'doughnut', chartData.appointment_status.labels, chartData.appointment_status.values, 'Appointments');
        renderChart('bedChart', 'doughnut', chartData.bed_occupancy.labels, chartData.bed_occupancy.values, 'Beds');
    }

    async function loadAnalytics() {
        status.textContent = '';
        page.classList.add('is-loading');
        applyButton.disabled = true;
        const params = new URLSearchParams({ start_date: startInput.value, end_date: endInput.value });
        if (departmentInput.value) params.set('department_id', departmentInput.value);
        try {
            const response = await fetch(`/api/analytics?${params.toString()}`, { headers: { Accept: 'application/json' } });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Analytics could not be loaded.');
            updateDashboard(data);
        } catch (error) {
            status.textContent = error.message || 'Analytics could not be loaded. Please try again.';
        } finally {
            page.classList.remove('is-loading');
            applyButton.disabled = false;
        }
    }

    applyButton.addEventListener('click', loadAnalytics);
    loadAnalytics();
}());