window.renderDailyChart = function renderDailyChart(points) {
  var labels = points.map(function (p) { return p.day; });
  var phishing = points.map(function (p) { return p.phishing; });
  var total = points.map(function (p) { return p.total; });

  var ctx = document.getElementById("daily-chart");
  if (!ctx) {
    return;
  }

  new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Total scanned",
          data: total,
          borderColor: "#2470dc",
          backgroundColor: "rgba(36, 112, 220, 0.15)",
          fill: true,
          tension: 0.3,
        },
        {
          label: "Phishing",
          data: phishing,
          borderColor: "#ce3f29",
          backgroundColor: "rgba(206, 63, 41, 0.15)",
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { position: "top" },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0 },
        },
      },
    },
  });
};

