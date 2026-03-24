import fs from "node:fs";

// Read the built-in k6 summary
const raw = JSON.parse(fs.readFileSync("sn-devops-results.json", "utf8"));
const metrics = raw.metrics;

// Extract metrics that actually exist
const http = metrics["http_req_duration{expected_response:true}"] || metrics.http_req_duration || {};
const iterations = metrics.iterations?.count || 0;
const durationSeconds = iterations > 0 ? iterations / metrics.http_reqs.rate : 0;

// Build the metrics block for ServiceNow
const perfMetrics = {
  maximumVirtualUsers: metrics.vus_max?.max || 0,
  throughput: metrics.http_reqs?.rate || 0,
  maximumTime: http.max || 0,
  minimumTime: http.min || 0,
  averageTime: http.avg || 0,
  ninetyPercent: http["p(90)"] || 0,
  standardDeviation: http.stddev || 0
};

// Build the full ServiceNow DevOps payload
const payload = {
  toolId: process.env.SN_TOOL_ID,
  buildNumber: process.env.GITHUB_RUN_NUMBER,
  buildId: process.env.GITHUB_RUN_ID,
  attemptNumber: "1",
  stageName: "test",
  workflow: process.env.GITHUB_WORKFLOW,
  repository: process.env.GITHUB_REPOSITORY,
  testSummaries: [
    {
      name: "Performance Test Summary",
      testType: "Load",
      startTime: new Date().toISOString(),
      endTime: new Date().toISOString(),
      duration: durationSeconds,
      metrics: perfMetrics
    }
  ]
};

// Write the transformed file
fs.writeFileSync("sn-devops-transformed.json", JSON.stringify(payload, null, 2));
console.log("Transformed k6 summary written to sn-devops-transformed.json");