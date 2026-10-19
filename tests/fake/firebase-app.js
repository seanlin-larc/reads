// Fake Firebase App for tests: keeps the config so getAuth can check the project.
export function initializeApp(c) { return { c }; }
