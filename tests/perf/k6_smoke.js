import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(50)<150', 'p(95)<350']
  }
};

export default function () {
  const r = http.get('http://localhost:8000/health');
  check(r, { '200': (res) => res.status === 200 });
  sleep(0.2);
}


