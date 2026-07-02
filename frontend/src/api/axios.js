import axios from 'axios';
import { API_ENDPOINT } from '../config/api'; // Import our endpoint

/**
 * Reads a cookie value by its name.
 * @param {string} name - The name of the cookie to find ('csrftoken').
 * @returns {string|null} The value of the cookie or null if not found.
 */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(
          cookie.substring(name.length + 1)
        );
        break;
      }
    }
  }
  return cookieValue;
}

// Added sleep helper for exponential backoff
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Create a pre-configured instance of axios.
 * This instance will have the base URL set, so we don't have to
 * repeat it in every API call.
 */
const axiosInstance = axios.create({
  baseURL: API_ENDPOINT,
  withCredentials: true,
  headers: {
    'X-CSRFToken': getCookie('csrftoken'),
    'Content-Type': 'application/json',
  },
});

// This function will be called from main.js after the store is created.
export const setupInterceptors = (store) => {
  axiosInstance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;

      // Prevent infinite loops by checking if the error came from
      // the refresh endpoint itself. If so, reject immediately.
      if (originalRequest.url.includes('/token/refresh/')) {
        return Promise.reject(error);
      }

      // Check if the error is a 401 Unauthorized and it's not a retry.
      if (
        error.response &&
        error.response.status === 401 &&
        !originalRequest._retry
      ) {
        originalRequest._retry = true;

        let retryCount = 0;
        const maxRetries = 3;

        while (retryCount < maxRetries) {
          try {
            const newAccessToken = await store.dispatch(
              'auth/tryRefreshToken'
            );

            originalRequest.headers['Authorization'] =
              `Bearer ${newAccessToken}`;
            return axiosInstance(originalRequest);
          } catch (refreshError) {
            // If the refresh token is invalid (401/400), stop retrying and logout.
            if (refreshError.response && (refreshError.response.status === 400 || refreshError.response.status === 401)) {
              store.dispatch('auth/logout');
              return Promise.reject(refreshError);
            }

            retryCount++;
            if (retryCount === maxRetries) {
              store.dispatch('auth/logout');
              return Promise.reject(refreshError);
            }

            const delay = Math.pow(2, retryCount - 1) * 1000;
            await sleep(delay);
          }
        }
      }
      return Promise.reject(error);
    }
  );
};

export default axiosInstance;
