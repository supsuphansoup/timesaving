import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Intercept responses to handle 401 Unauthorized globally
client.interceptors.response.use(
  (response) => {
    if (response.data && typeof response.data === 'object' && response.data.success === true && 'data' in response.data) {
      response.data = response.data.data;
    }
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear localStorage
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      // If we are not already on the login page, reload to trigger a redirect
      if (window.location.pathname !== '/') {
        window.location.reload();
      }
    }
    return Promise.reject(error);
  }
);

export default client;
