/**
 * Retrieves the value of a cookie by its name.
 * @param {string} name - The name of the cookie.
 * @returns {string|null} The cookie value, or null if not found.
 */
export const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(';').shift();
  }
  return null;
};

/**
 * Sets a cookie with a specified name, value, and expiration in days.
 * @param {string} name - The name of the cookie.
 * @param {string} value - The value to store.
 * @param {number} [days=365] - Number of days until the cookie expires.
 */
export const setCookie = (name, value, days = 365) => {
  let expires = "";
  if (days) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    expires = "; expires=" + date.toUTCString();
  }
  // protection against CSRF attacks
  document.cookie = `${name}=${value || ""}${expires}; path=/; SameSite=Lax`;
};

/**
 * Deletes a cookie by setting its expiration date to the past.
 * @param {string} name - The name of the cookie to delete.
 */
export const deleteCookie = (name) => {
  document.cookie = `${name}=; Max-Age=-99999999; path=/; SameSite=Lax`;
};
