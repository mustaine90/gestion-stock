// ==================== COMPTEURS ANIMÉS ====================
function animateCounter(element, target) {
    let current = 0;
    const increment = target / 50;
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current);
        }
    }, 20);
}

function initCounters() {
    document.querySelectorAll('.stat-card[data-count]').forEach(card => {
        const valueEl = card.querySelector('.stat-value');
        const target = parseFloat(card.dataset.count);
        if (!isNaN(target) && valueEl) {
            animateCounter(valueEl, target);
        }
    });
}

// ==================== DERNIERS MOUVEMENTS ====================
function loadRecentMovements() {
    fetch('/api/recent_movements')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('recentMovements');
            if (!container) return;

            if (data.length === 0) {
                container.innerHTML = '<div class="activity-item"><i class="fas fa-info-circle"></i> Aucun mouvement récent</div>';
                return;
            }

            let html = '';
            data.forEach(m => {
                const isEntree = m.type_mouvement.includes('entree');
                const icon = isEntree ? 'fa-arrow-down text-success' : 'fa-arrow-up text-danger';
                const typeLabel = isEntree ? 'Entrée' : 'Sortie';
                const dateFormatted = new Date(m.date_mouvement).toLocaleString('fr-FR', {
                    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
                });

                html += `
                    <div class="activity-item">
                        <i class="fas ${icon}"></i>
                        <div class="activity-details">
                            <span class="activity-title">${m.designation}</span>
                            <span class="activity-meta">${typeLabel} · ${m.quantite} unité(s) · ${dateFormatted}</span>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        })
        .catch(error => {
            console.error('Erreur chargement mouvements:', error);
            const container = document.getElementById('recentMovements');
            if (container) container.innerHTML = '<div class="activity-item text-danger">Erreur de chargement</div>';
        });
}

// ==================== JAUGE DE TAUX DE ROTATION ====================
let rotationGaugeInstance = null;

function drawRotationGauge(value) {
    const canvas = document.getElementById('rotationGauge');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (rotationGaugeInstance) rotationGaugeInstance.destroy();
    
    rotationGaugeInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [value, 10 - value],
                backgroundColor: ['#3b82f6', '#e2e8f0'],
                borderWidth: 0,
                circumference: 180,
                rotation: 270
            }]
        },
        options: {
            cutout: '75%',
            plugins: { tooltip: { enabled: false }, legend: { display: false } }
        }
    });
    const valueEl = document.getElementById('tauxRotationValue');
    if (valueEl) valueEl.textContent = value.toFixed(1);
}

// ==================== JAUGE DE NIVEAU DE STOCK GLOBAL ====================
let stockGaugeChart = null;

function initStockLevelGauge() {
    fetch('/api/niveau_stock_global')
        .then(response => response.json())
        .then(data => {
            const total = data.total;
            const capacite = data.capacite;
            const pourcentage = data.pourcentage;

            const pctEl = document.getElementById('stockPercentage');
            const detailsEl = document.getElementById('stockDetails');
            if (pctEl) pctEl.textContent = pourcentage + '%';
            if (detailsEl) detailsEl.textContent = `${total} / ${capacite} unités`;

            const canvas = document.getElementById('stockLevelGauge');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            
            if (stockGaugeChart) stockGaugeChart.destroy();

            stockGaugeChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [total, Math.max(0, capacite - total)],
                        backgroundColor: [
                            total > capacite ? '#ef4444' : '#3b82f6',
                            '#e2e8f0'
                        ],
                        borderWidth: 0,
                        borderRadius: total > capacite ? 0 : 10,
                    }]
                },
                options: {
                    cutout: '75%',
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        tooltip: { enabled: false },
                        legend: { display: false }
                    }
                }
            });
        })
        .catch(error => console.error('Erreur niveau stock:', error));
}

// ==================== GRAPHIQUE ÉVOLUTION DU STOCK CUMULÉ ====================
let evolutionChartInstance = null;
let evolutionChartLoading = false;

function loadEvolutionChart(periode = '30') {
    if (evolutionChartLoading) return;
    evolutionChartLoading = true;

    const canvas = document.getElementById('evolutionChart');
    if (!canvas) {
        evolutionChartLoading = false;
        return;
    }

    if (evolutionChartInstance) {
        evolutionChartInstance.destroy();
        evolutionChartInstance = null;
    }

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    fetch(`/api/evolution_stock_cumule?periode=${periode}`)
        .then(response => response.json())
        .then(data => {
            if (!document.getElementById('evolutionChart')) {
                evolutionChartLoading = false;
                return;
            }

            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(54, 162, 235, 0.4)');
            gradient.addColorStop(1, 'rgba(54, 162, 235, 0.0)');

            evolutionChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Stock cumulé',
                        data: data.stock_cumule,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: gradient,
                        borderWidth: 3,
                        pointBackgroundColor: 'rgb(54, 162, 235)',
                        pointBorderColor: 'white',
                        pointBorderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (context) => `Stock: ${context.raw} unités`
                            }
                        },
                        legend: { display: true, position: 'top' }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Quantité en stock' }
                        },
                        x: {
                            title: { display: true, text: 'Date' }
                        }
                    },
                    interaction: { mode: 'index', intersect: false }
                }
            });
            evolutionChartLoading = false;
        })
        .catch(error => {
            console.error('Erreur chargement évolution stock:', error);
            evolutionChartLoading = false;
        });
}

function initPeriodeButtons() {
    const container = document.querySelector('.periode-selector');
    if (!container) return;
    // On utilise la délégation d'événements pour éviter les doublons
    container.addEventListener('click', handlePeriodeClick);
}

function handlePeriodeClick(e) {
    const btn = e.target.closest('.periode-btn');
    if (!btn) return;
    e.preventDefault();
    document.querySelectorAll('.periode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadEvolutionChart(btn.dataset.periode);
}

// ==================== TOP 5 ARTICLES PAR VALEUR ====================
let repartitionChartInstance = null;

function loadRepartitionChart() {
    fetch('/api/repartition_stock')
        .then(response => response.json())
        .then(data => {
            const canvas = document.getElementById('repartitionChart');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');

            if (repartitionChartInstance) {
                repartitionChartInstance.destroy();
            }

            repartitionChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Valeur totale (€)',
                        data: data.valeurs,
                        backgroundColor: function(context) {
                            const chart = context.chart;
                            const {ctx, chartArea} = chart;
                            if (!chartArea) return 'rgba(54, 162, 235, 0.8)';
                            const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                            gradient.addColorStop(0, 'rgba(54, 162, 235, 0.8)');
                            gradient.addColorStop(1, 'rgba(153, 102, 255, 0.8)');
                            return gradient;
                        },
                        borderRadius: 6,
                        barPercentage: 0.6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `${ctx.raw.toFixed(2)} €`
                            }
                        },
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Valeur (€)'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Erreur chargement top articles:', error));
}

// ==================== RÉPARTITION DES MOUVEMENTS PAR TYPE ====================
let mouvementTypeChartInstance = null;

function loadMouvementsParType() {
    const canvas = document.getElementById('typeChart');
    if (!canvas) return;

    // Forcer une hauteur fixe pour empêcher l'agrandissement
    canvas.style.height = '280px';
    canvas.height = 280;

    if (mouvementTypeChartInstance) {
        mouvementTypeChartInstance.destroy();
        mouvementTypeChartInstance = null;
    }

    const ctx = canvas.getContext('2d');

    fetch('/api/mouvements_par_type')
        .then(r => r.json())
        .then(data => {
            if (!document.getElementById('typeChart')) return;

            mouvementTypeChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.valeurs,
                        backgroundColor: ['#4BC0C0', '#FF6384', '#FFCE56', '#36A2EB']
                    }]
                },
                options: {
                    responsive: false,               // <-- empêche les redimensionnements
                    maintainAspectRatio: false,
                    animation: false,                // pas d'animation parasite
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    let total = ctx.dataset.data.reduce((a,b) => a+b, 0);
                                    let percentage = ((ctx.raw / total) * 100).toFixed(1);
                                    return `${ctx.label}: ${ctx.raw} (${percentage}%)`;
                                }
                            }
                        },
                        legend: { position: 'bottom' }
                    }
                }
            });
        })
        .catch(error => console.error('Erreur chargement répartition mouvements:', error));
}
// ==================== TOP CONSOMMATIONS (articles les plus sortis) ====================
let topConsoChartInstance = null;

function loadTopConsommations() {
    fetch('/api/top_consommations')
        .then(r => r.json())
        .then(data => {
            const canvas = document.getElementById('topConsoChart');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');

            if (topConsoChartInstance) {
                topConsoChartInstance.destroy();
            }

            topConsoChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Quantité sortie',
                        data: data.valeurs,
                        backgroundColor: '#FF6384',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `${ctx.raw} unités`
                            }
                        },
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Quantité' }
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Erreur chargement top consommations:', error));
}

// ==================== RAFRAÎCHIR TOUT ====================
function refreshAllData() {
    location.reload();
}

// ==================== INITIALISATION GLOBALE ====================
document.addEventListener('DOMContentLoaded', function() {
    // Compteurs animés
    initCounters();
    // Derniers mouvements
    loadRecentMovements();
    // Jauges
    initStockLevelGauge();
    drawRotationGauge(0); // sera mis à jour ci-dessous
    // Graphiques
    loadEvolutionChart('30');
    loadRepartitionChart();
    loadMouvementsParType();
    loadTopConsommations();

    // Gestion des boutons de période
    initPeriodeButtons();

    // Mise à jour du taux de rotation réel
    fetch('/api/stats_complementaires')
        .then(r => r.json())
        .then(stats => drawRotationGauge(stats.taux_rotation))
        .catch(e => console.error('Erreur stats:', e));

    // Actualisations périodiques (optionnel)
    setInterval(loadRecentMovements, 60000);
    setInterval(initStockLevelGauge, 300000);
});