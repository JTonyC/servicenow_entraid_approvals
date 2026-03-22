import http from 'k6/http';
import { check, sleep } from 'k6';
import { jUnit } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';

export let options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    checks: ['rate>0'],
  },
};

export default function () {
  const res = http.get(`${__ENV.TARGET_URL}/`);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'body is not empty': (r) => r.body && r.body.length > 0,
  });

  sleep(1);
}

export function handleSummary(data) {
  const metrics = data.metrics;

  const httpReqs = metrics.http_reqs ? metrics.http_reqs.count : 0;
  const httpDuration = metrics.http_req_duration || {};

  const totalDurationSeconds = data.state.testRunDurationMs / 1000;
  const throughput = totalDurationSeconds > 0
    ? Number((httpReqs / totalDurationSeconds).toFixed(2))
    : 0;

  const payload = {
    // High-level test metadata
    testType: "Load",          // maps to the Load test type in Change Velocity
    testToolName: "k6",
    testName: "k6 Smoke Test",

    // Timing
    startTime: new Date(data.state.testRunStart).toISOString(),
    endTime: new Date().toISOString(),

    // Core performance metrics
    testResult: {
      maxVirtualUsers: metrics.vus ? metrics.vus.max : 0,
      totalRequests: httpReqs,
      throughput, // req/s
      maxTime: httpDuration.max || 0,
      minTime: httpDuration.min || 0,
      avgTime: httpDuration.avg || 0,
      p90: httpDuration["p(90)"] || 0,
      stddev: httpDuration.stddev || 0
    }
  };

  return {
    "sn-devops-results.json": JSON.stringify(payload, null, 2)
  };
}