import fs from "node:fs";

const raw = JSON.parse(fs.readFileSync("sn-devops-results.json", "utf8"));
const metrics = raw.metrics;

const http = metrics["http_req_duration{expected_response:true}"] || metrics.http_req_duration || {};

// Derive meaningful test summary values
const totalTests = metrics.http_reqs?.count || 0;
const passedTests = metrics["http_reqs{expected_response:true}"]?.count || totalTests;
const failedTests = metrics["http_reqs{expected_response:false}"]?.count || 0;

const iterations = metrics.iterations?.count || 0;
const durationSeconds = iterations > 0 ? iterations / metrics.http_reqs.rate : 0;

const start = new Date().toISOString();
const end = new Date().toISOString();

const payload = {
  // Required top-level fields (unchanged)
  toolId: process.env.SN_TOOL_ID,
  testType: "Load",

  workflow: process.env.GITHUB_WORKFLOW,
  repository: process.env.GITHUB_REPOSITORY,

  pipelineName: `${process.env.GITHUB_REPOSITORY}/${process.env.GITHUB_WORKFLOW}`,
  stageName: "test",

  buildNumber: process.env.GITHUB_RUN_NUMBER,
  buildId: process.env.GITHUB_RUN_ID,
  attemptNumber: process.env.GITHUB_RUN_ATTEMPT,

  url: `https://github.com/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`,
  name: "k6 Performance Test",

  // ⭐ NEW: Test Tool Integration-compliant testSummaries
  testSummaries: [
    {
      name: "k6 Performance Test",
      testType: "Load",

      // Required fields for Test Tool Integration
      totalTests: totalTests,
      passedTests: passedTests,
      failedTests: failedTests,
      skippedTests: 0,
      blockedTests: 0,
      ignoredTests: 0,

      duration: durationSeconds,
      startTime: start,
      endTime: end,
      suites: [],

      // ⭐ Performance metrics moved here (schema‑safe)
      maximumVirtualUsers: metrics.vus_max?.max || 0,
      throughput: metrics.http_reqs?.rate || 0,
      maximumTime: http.max || 0,
      minimumTime: http.min || 0,
      averageTime: http.avg || 0,
      ninetyPercent: http["p(90)"] || 0,
      standardDeviation: http.stddev || 0
    }
  ]
};

fs.writeFileSync("sn-devops-perf.json", JSON.stringify(payload, null, 2));
console.log("Transformed k6 summary written to sn-devops-perf.json");