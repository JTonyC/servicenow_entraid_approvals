import fs from "node:fs";

const raw = JSON.parse(fs.readFileSync("sn-devops-results.json", "utf8"));
const metrics = raw.metrics;

const http = metrics["http_req_duration{expected_response:true}"] || metrics.http_req_duration || {};

const iterations = metrics.iterations?.count || 0;
const durationSeconds = iterations > 0 ? iterations / metrics.http_reqs.rate : 0;

const payload = {
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

  // Required timestamps
  startTime: start,
  finishTime: end,

  // Required metrics (correct types)
  duration: durationSeconds,                                 // number
  maximumVirtualUsers: metrics.vus_max?.max || 0,            // number
  throughput: String(metrics.http_reqs?.rate || 0),          // string
  maximumTime: http.max || 0,                                // number
  minimumTime: http.min || 0,                                // number
  averageTime: http.avg || 0,                                // number
  ninetyPercent: http["p(90)"] || 0,                         // number
  standardDeviation: http.stddev || 0                        // number

};

fs.writeFileSync("sn-devops-perf.json", JSON.stringify(payload, null, 2));
console.log("Performance Test Summary payload written to sn-devops-perf.json");