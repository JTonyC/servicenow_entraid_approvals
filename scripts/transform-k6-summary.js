import fs from "node:fs";

const raw = JSON.parse(fs.readFileSync("sn-devops-results.json", "utf8"));
const metrics = raw.metrics;

const http = metrics["http_req_duration{expected_response:true}"] || metrics.http_req_duration || {};
const iterations = metrics.iterations?.count || 0;
const durationSeconds = iterations > 0 ? iterations / metrics.http_reqs.rate : 0;

const payload = {
  toolId: process.env.SN_TOOL_ID,

  name: "k6 Performance Test",
  url: `https://github.com/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`,

  startTime: new Date().toISOString(),
  finishTime: new Date().toISOString(),
  duration: durationSeconds,

  maximumVirtualUsers: metrics.vus_max?.max || 0,
  throughput: metrics.http_reqs?.rate || 0,
  maximumTime: http.max || 0,
  minimumTime: http.min || 0,
  averageTime: http.avg || 0,
  ninetyPercent: http["p(90)"] || 0,
  standardDeviation: http.stddev || 0,

  buildNumber: process.env.GITHUB_RUN_NUMBER,
  buildId: process.env.GITHUB_RUN_ID,
  attemptNumber: "1",

  stageName: "test",
  pipelineName: `${process.env.GITHUB_REPOSITORY}/${process.env.GITHUB_WORKFLOW}`,

  testType: "Load"
};

fs.writeFileSync("sn-devops-perf.json", JSON.stringify(payload, null, 2));
console.log("Transformed k6 summary written to sn-devops-perf.json");
