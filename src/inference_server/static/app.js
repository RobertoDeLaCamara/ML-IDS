/**
 * ML-IDS Dashboard Application
 * Fetches data from API and displays real-time alerts via WebSocket
 */

const API_BASE = '/api/dashboard';
const WS_URL = `ws://${window.location.host}/api/dashboard/live`;

let ws = null;
let timelineChart = null;
let distributionChart = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    fetchDashboardData();
    connectWebSocket();

    // Refresh data every 30 seconds
    setInterval(fetchDashboardData, 30000);
});

/**
 * Initialize Chart.js charts
 */
function initializeCharts() {
    // Attack Timeline Chart
    const timelineCtx = document.getElementById('timeline-chart').getContext('2d');
    timelineChart = new Chart(timelineCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Critical',
                data: [],
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                tension: 0.4
            }, {
                label: 'High',
                data: [],
                borderColor: '#ff9800',
                backgroundColor: 'rgba(255, 152, 0, 0.1)',
                tension: 0.4
            }, {
                label: 'Medium',
                data: [],
                borderColor: '#ffc107',
                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                tension: 0.4
            }, {
                label: 'Low',
                data: [],
                borderColor: '#36a64f',
                backgroundColor: 'rgba(54, 166, 79, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });

    // Attack Distribution Chart
    const distributionCtx = document.getElementById('distribution-chart').getContext('2d');
    distributionChart = new Chart(distributionCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#dc3545', '#ff9800', '#ffc107', '#36a64f', '#2196f3',
                    '#9c27b0', '#00bcd4', '#ff5722', '#607d8b', '#cddc39'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

/**
 * Fetch all dashboard data
 */
async function fetchDashboardData() {
    try {
        await Promise.all([
            fetchStats(),
            fetchTimeline(),
            fetchTopAttackers(),
            fetchDistribution(),
            fetchRecentAlerts()
        ]);

        updateLastUpdated();
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
    }
}

/**
 * Fetch overall statistics
 */
async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE}/stats?hours=24`);
        const data = await response.json();

        document.getElementById('total-alerts').textContent = data.total_alerts || 0;
        document.getElementById('active-incidents').textContent = data.active_incidents || 0;
        document.getElementById('critical-alerts').textContent = data.alerts_by_severity?.critical || 0;
        document.getElementById('high-alerts').textContent = data.alerts_by_severity?.high || 0;
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

/**
 * Fetch and update attack timeline chart
 */
async function fetchTimeline() {
    try {
        const response = await fetch(`${API_BASE}/attack-timeline?hours=24&interval_minutes=60`);
        const data = await response.json();

        if (data.data && data.data.length > 0) {
            const labels = data.data.map(item => {
                const date = new Date(item.timestamp);
                return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            });

            timelineChart.data.labels = labels;
            timelineChart.data.datasets[0].data = data.data.map(item => item.critical);
            timelineChart.data.datasets[1].data = data.data.map(item => item.high);
            timelineChart.data.datasets[2].data = data.data.map(item => item.medium);
            timelineChart.data.datasets[3].data = data.data.map(item => item.low);
            timelineChart.update();
        }
    } catch (error) {
        console.error('Error fetching timeline:', error);
    }
}

/**
 * Fetch and update attack distribution chart
 */
async function fetchDistribution() {
    try {
        const response = await fetch(`${API_BASE}/attack-distribution?hours=24`);
        const data = await response.json();

        if (data.distribution && data.distribution.length > 0) {
            distributionChart.data.labels = data.distribution.map(item => item.attack_type);
            distributionChart.data.datasets[0].data = data.distribution.map(item => item.count);
            distributionChart.update();
        }
    } catch (error) {
        console.error('Error fetching distribution:', error);
    }
}

/**
 * Fetch and display top attackers
 */
async function fetchTopAttackers() {
    try {
        const response = await fetch(`${API_BASE}/top-attackers?hours=24&limit=10`);
        const data = await response.json();

        const tbody = document.getElementById('attackers-tbody');

        if (data.attackers && data.attackers.length > 0) {
            tbody.innerHTML = data.attackers.map(attacker => `
                <tr>
                    <td><code>${attacker.src_ip}</code></td>
                    <td>${attacker.attack_count}</td>
                    <td><span class="severity-badge severity-${attacker.max_severity}">${attacker.max_severity}</span></td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No data available</td></tr>';
        }
    } catch (error) {
        console.error('Error fetching top attackers:', error);
    }
}

/**
 * Fetch and display recent alerts
 */
async function fetchRecentAlerts() {
    try {
        const response = await fetch(`${API_BASE}/recent-alerts?limit=20`);
        const data = await response.json();

        const container = document.getElementById('alerts-container');

        if (data.alerts && data.alerts.length > 0) {
            container.innerHTML = data.alerts.map(alert => createAlertElement(alert)).join('');
        } else {
            container.innerHTML = '<p class="empty-state">No alerts yet...</p>';
        }
    } catch (error) {
        console.error('Error fetching recent alerts:', error);
    }
}

/**
 * Create HTML element for an alert
 */
function createAlertElement(alert) {
    const timestamp = new Date(alert.timestamp).toLocaleString();
    return `
        <div class="alert-item severity-${alert.severity}">
            <div class="alert-header">
                <span class="severity-badge severity-${alert.severity}">${alert.severity.toUpperCase()}</span>
                <span class="alert-time">${timestamp}</span>
            </div>
            <div class="alert-body">
                <strong>${alert.attack_type}</strong> from <code>${alert.src_ip}</code>
            </div>
            ${alert.acknowledged ? '<div class="alert-ack">✓ Acknowledged</div>' : ''}
        </div>
    `;
}

/**
 * Connect to WebSocket for real-time updates
 */
function connectWebSocket() {
    try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);
            reconnectAttempts = 0;
        };

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateConnectionStatus(false);
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            updateConnectionStatus(false);

            // Attempt to reconnect
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
                setTimeout(connectWebSocket, delay);
            }
        };
    } catch (error) {
        console.error('Failed to create WebSocket:', error);
        updateConnectionStatus(false);
    }
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(message) {
    if (message.type === 'alert') {
        // New alert received
        addNewAlert(message.data);

        // Refresh stats
        fetchStats();

        // Show notification (if supported)
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('New Security Alert', {
                body: `${message.data.severity.toUpperCase()}: ${message.data.attack_type} from ${message.data.src_ip}`,
                icon: '/favicon.ico'
            });
        }
    } else if (message.type === 'stats_update') {
        // Stats update received
        fetchStats();
    }
}

/**
 * Add new alert to the feed
 */
function addNewAlert(alert) {
    const container = document.getElementById('alerts-container');

    // Remove empty state if present
    if (container.querySelector('.empty-state')) {
        container.innerHTML = '';
    }

    // Prepend new alert
    const alertElement = createAlertElement(alert);
    container.insertAdjacentHTML('afterbegin', alertElement);

    // Limit to 20 alerts in the feed
    const alerts = container.querySelectorAll('.alert-item');
    if (alerts.length > 20) {
        alerts[alerts.length - 1].remove();
    }

    // Add animation
    const newAlert = container.firstElementChild;
    newAlert.style.animation = 'slideIn 0.3s ease-out';
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connection-indicator');
    const text = document.getElementById('connection-text');

    if (connected) {
        indicator.className = 'status-dot connected';
        text.textContent = 'Live';
    } else {
        indicator.className = 'status-dot disconnected';
        text.textContent = 'Disconnected';
    }
}

/**
 * Update last updated timestamp
 */
function updateLastUpdated() {
    document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
}

// Request notification permission on load
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}
