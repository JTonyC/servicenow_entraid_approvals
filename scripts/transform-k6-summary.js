import fs from "node:fs";

const raw = JSON.parse(fs.readFileSync("sn-devops-results.json", "utf8"));
console.log("STATE:", raw.state);
const metrics = raw.metrics;

const http = metrics["http_req_duration{expected_response:true}"] || metrics.http_req_duration || {};

const iterations = metrics.iterations?.count || 0;
const durationSeconds = iterations > 0 ? iterations / metrics.http_reqs.rate : 0;

const startTimeRaw = raw.state?.testRunStart || raw.state?.testRunStartTime;
const endTimeRaw = raw.state?.testRunEnd || raw.state?.testRunEndTime;
const start = new Date(startTimeRaw).toISOString();
const end = new Date(endTimeRaw).toISOString();

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
  duration: durationSeconds,                                        // number
  maximumVirtualUsers: metrics.vus_max?.max || 0,                   // number
  throughput: `${(metrics.http_reqs?.rate * 60).toFixed(0)}/min`,   // string
  maximumTime: Math.round(http.max * 1000),                         // number
  minimumTime: Math.round(http.min * 1000) || 0,                    // number
  averageTime: Math.round(http.avg * 1000) || 0,                    // number
  ninetyPercent: Math.round(http["p(90)"] * 1000) || 0,             // number
  standardDeviation: Math.round(http.stddev * 1000)                 // number

};

fs.writeFileSync("sn-devops-perf.json", JSON.stringify(payload, null, 2));
console.log("Performance Test Summary payload written to sn-devops-perf.json");