import axios from 'axios';

let port = (!process.env.NODE_ENV || process.env.NODE_ENV === 'development') ? 8000 : window.location.port;
export const api = axios.create({
  baseURL: `http://${window.location.hostname}:${port}`,
})