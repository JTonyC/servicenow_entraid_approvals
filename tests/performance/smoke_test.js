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

  // Extract metrics
  const vus = metrics.vus.max;
  const httpReqs = metrics.http_reqs ? metrics.http_reqs.count : 0;

  const httpDuration = metrics.http_req_duration;
  const maxTime = httpDuration ? httpDuration.max : 0;
  const minTime = httpDuration ? httpDuration.min : 0;
  const avgTime = httpDuration ? httpDuration.avg : 0;
  const p90 = httpDuration ? httpDuration['p(90)'] : 0;
  const stddev = httpDuration ? httpDuration.stddev : 0;

  // Throughput = total requests / total duration (seconds)
  const totalDurationSeconds = data.state.testRunDurationMs / 1000;
  const throughput = totalDurationSeconds > 0
    ? (httpReqs / totalDurationSeconds).toFixed(2)
    : 0;

  // Build JUnit XML
  const xml = `
<testsuite name="Performance Summary" tests="7">
  <testcase name="Max Virtual Users" classname="Performance">
    <system-out>${vus}</system-out>
  </testcase>
  <testcase name="Throughput (req/s)" classname="Performance">
    <system-out>${throughput}</system-out>
  </testcase>
  <testcase name="Max Time (ms)" classname="Performance">
    <system-out>${maxTime}</system-out>
  </testcase>
  <testcase name="Min Time (ms)" classname="Performance">
    <system-out>${minTime}</system-out>
  </testcase>
  <testcase name="Average Time (ms)" classname="Performance">
    <system-out>${avgTime}</system-out>
  </testcase>
  <testcase name="90th Percentile (ms)" classname="Performance">
    <system-out>${p90}</system-out>
  </testcase>
  <testcase name="Standard Deviation (ms)" classname="Performance">
    <system-out>${stddev}</system-out>
  </testcase>
</testsuite>
`.trim();

  return {
    "perf-results.xml": xml,
  };
}