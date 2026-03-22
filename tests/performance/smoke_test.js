import http from 'k6/http';
import { check, sleep } from 'k6';
import { convert } from 'k6-to-junit';

export let options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
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
  return {
    'perf-results.xml': convert(data),
  };
}