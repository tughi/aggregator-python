FROM node:18-alpine as build

WORKDIR /app

COPY package.json yarn.lock ./

RUN yarn

COPY index.html ./
COPY public ./public/
COPY src ./src/
COPY vite.config.js ./

RUN yarn build

FROM nginx:stable-alpine

RUN rm -fr /usr/share/nginx/html/*

COPY --from=build /app/dist /usr/share/nginx/html

COPY ./nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
