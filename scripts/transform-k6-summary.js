import fs from "node:fs";

// Read the built-in k6 summary
const raw = JSON.parse(fs.readFileSync("sn-devops-results.json", "utf8"));
const metrics = raw.metrics;

// Extract the metrics you actually have
const http = metrics["http_req_duration{expected_response:true}"] || metrics.http_req_duration || {};
const iterations = metrics.iterations?.count || 0;
const durationSeconds = iterations > 0 ? iterations / metrics.http_reqs.rate : 0;

// Build the ServiceNow payload
const payload = {
  name: "k6 Performance Test",
  url: process.env.GITHUB_SERVER_URL + "/" +
       process.env.GITHUB_REPOSITORY + "/actions/runs/" +
       process.env.GITHUB_RUN_ID,

  startTime: new Date().toISOString(),
  finishTime: new Date().toISOString(),
  duration: durationSeconds,

  maximumVirtualUsers: metrics.vus_max?.max || 0,
  throughput: metrics.http_reqs?.rate || 0,

  maximumTime: http.max || 0,
  minimumTime: http.min || 0,
  averageTime: http.avg || 0,
  ninetyPercent: http["p(90)"] || 0,
  standardDeviation: http.stddev || 0, // may be undefined

  buildNumber: process.env.GITHUB_RUN_NUMBER,
  stageName: "test",
  pipelineName: "JTonyC/servicenow_entraid_approvals/Build and deploy Python app to Azure Web App - tcazr-test-webapp"
};

// Write the transformed file
fs.writeFileSync("sn-devops-transformed.json", JSON.stringify(payload, null, 2));
console.log("Transformed k6 summary written to sn-devops-transformed.json");