import axios from 'axios';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || '/api';

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000
});

request.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('token');
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
  const baseUrl = /^https?:\/\//i.test(API_BASE_URL)
    ? API_BASE_URL
    : `${window.location.origin}${API_BASE_URL.startsWith('/') ? '' : '/'}${API_BASE_URL}`;
  const url = new URL(baseUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = '/ws';
  url.search = new URLSearchParams({ token }).toString();
  return url.toString();
};

export default request;
