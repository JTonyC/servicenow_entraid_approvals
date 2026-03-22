import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 10,               // 10 virtual users
  duration: '30s',       // run for 30 seconds
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],     // < 1% errors allowed
  },
};

export default function () {
  const res = http.get(`${__ENV.TARGET_URL}/`);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'body is not empty': (r) => r.body && r.body.length > 0,
  });

  sleep(1); // small pacing delay
}