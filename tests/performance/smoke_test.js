import http from 'k6/http';
import { check, sleep } from 'k6';

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

  console.log(JSON.stringify(Object.keys(metrics), null, 2));
  const metrics = data.metrics;

  const httpReqs = metrics.http_reqs ? metrics.http_reqs.count : 0;
  const httpDuration = metrics["http_req_duration{expected_response:true}"] || metrics.http_req_duration || {};

  const totalDurationSeconds = (data.state?.testRunDurationMs || 0) / 1000;
  const throughput = totalDurationSeconds > 0
    ? Number((httpReqs / totalDurationSeconds).toFixed(2))
    : 0;

  const payload = {

    name: "k6 Performance Test",
    url: `${__ENV.GITHUB_SERVER_URL}/${__ENV.GITHUB_REPOSITORY}/actions/runs/${__ENV.GITHUB_RUN_ID}`,

    startTime: new Date(data.state?.testRunStart || Date.now()).toISOString(),
    finishTime: new Date(Date.now()).toISOString(),
    duration: totalDurationSeconds,

    maximumVirtualUsers: metrics.vus_max ? metrics.vus_max.value : 0,
    throughput: Number(throughput) || 0,
    maximumTime: httpDuration.max || 0,
    minimumTime: httpDuration.min || 0,
    averageTime: httpDuration.avg || 0,
    ninetyPercent: httpDuration["p(90)"] || 0,
    standardDeviation: httpDuration.stddev || 0,

    // Pipeline binding (must match your SN pipeline)
    buildNumber: __ENV.GITHUB_RUN_NUMBER,
    stageName: "test",
    pipelineName: "JTonyC/servicenow_entraid_approvals/Build and deploy Python app to Azure Web App - tcazr-test-webapp"
  };

    return {
        [`${__ENV.K6_SUMMARY_EXPORT_PATH}/sn-devops-results.json`]: JSON.stringify(payload, null, 2)
    };
}