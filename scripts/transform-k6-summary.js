import fs from "node:fs";

const raw = JSON.parse(fs.readFileSync("sn-devops-results.json", "utf8"));
const metrics = raw.metrics;

const http = metrics["http_req_duration{expected_response:true}"] || metrics.http_req_duration || {};

const iterations = metrics.iterations?.count || 0;
const durationSeconds = iterations > 0 ? iterations / metrics.http_reqs.rate : 0;

const start = new Date().toISOString();
const end = new Date().toISOString();

const payload = {
  name: "k6 Performance Test",
  url: `https://github.com/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`,

  startTime: start,
  finishTime: end,

  // duration is the ONLY numeric field
  duration: durationSeconds,

  // All other metrics MUST be strings
  maximumVirtualUsers: String(metrics.vus_max?.max || 0),
  throughput: String(metrics.http_reqs?.rate || 0),
  maximumTime: String(http.max || 0),
  minimumTime: String(http.min || 0),
  averageTime: String(http.avg || 0),
  ninetyPercent: String(http["p(90)"] || 0),
  standardDeviation: String(http.stddev || 0),

  // Build + stage + pipelineName (your chosen combination)
  buildNumber: process.env.GITHUB_RUN_NUMBER,
  stageName: "test",
  pipelineName: `${process.env.GITHUB_REPOSITORY}/${process.env.GITHUB_WORKFLOW}`
};

fs.writeFileSync("sn-devops-perf.json", JSON.stringify(payload, null, 2));
console.log("Performance Test payload written to sn-devops-perf.json");