/// <reference types="vite/client" />

// Vite ?raw imports — return the raw source string
declare module '*.vue?raw' {
  const content: string
  export default content
}
declare module '*?raw' {
  const content: string
  export default content
}
