const { createProxyMiddleware } = require('http-proxy-middleware')

module.exports = (app) => {
   app.use(
      '/graphql',
      createProxyMiddleware({
         target: 'http://localhost:8000',
         changeOrigin: true,
      })
   )
}
