import http from 'k6/http';
import { check, sleep } from 'k6';
import { jUnit } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';

export let options = {
  vus: 10,
  duration: '30s',
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
    'perf-results.xml': jUnit(data),
  };
}