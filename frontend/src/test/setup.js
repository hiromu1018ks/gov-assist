import '@testing-library/jest-dom/vitest';
import { JSDOM } from 'jsdom';

// Node.js 25+ ships a built-in localStorage stub (Web Storage API) that
// conflicts with jsdom's localStorage. The stub lacks clear/getItem/setItem.
// Work around it by creating a jsdom instance and reassigning globalThis.localStorage.
const { localStorage: jsdomStorage } = new JSDOM('', { url: 'http://localhost' }).window;
Object.defineProperty(globalThis, 'localStorage', {
  value: jsdomStorage,
  writable: true,
  configurable: true,
});
