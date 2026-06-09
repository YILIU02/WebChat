import axios from 'axios';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8083/api';

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000
});

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const method = String(config.method || 'get').toLowerCase();
  const hasBody = !['get', 'head'].includes(method) && config.data !== undefined;

  if (hasBody && !(config.data instanceof FormData) && !config.headers['Content-Type']) {
    config.headers['Content-Type'] = 'application/json';
  }

  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }

  return config;
});

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.errMsg ||
      error.response?.data?.message ||
      error.message ||
      '请求失败';

    return Promise.reject(new Error(message));
  }
);

export const getErrorMessage = (error) => error?.message || '请求失败';

export const buildWebSocketUrl = (token) => {
  const url = new URL(API_BASE_URL);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = '/ws';
  url.search = new URLSearchParams({ token }).toString();
  return url.toString();
};

export default request;
