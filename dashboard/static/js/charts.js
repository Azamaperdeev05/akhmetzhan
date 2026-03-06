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
          label: "Барлық скан",
          data: total,
          borderColor: "#24c5ff",
          backgroundColor: "rgba(36, 197, 255, 0.2)",
          fill: true,
          tension: 0.35,
          pointRadius: 2,
        },
        {
          label: "Фишинг",
          data: phishing,
          borderColor: "#ff5d5d",
          backgroundColor: "rgba(255, 93, 93, 0.2)",
          fill: true,
          tension: 0.35,
          pointRadius: 2,
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
          grid: {
            color: "rgba(255,255,255,0.08)",
          },
        },
        x: {
          grid: {
            color: "rgba(255,255,255,0.04)",
          },
        },
      },
    },
  });
};
