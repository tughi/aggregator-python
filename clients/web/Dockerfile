FROM node:14-alpine as build

WORKDIR /app

COPY package.json yarn.lock ./
RUN yarn

COPY public ./public/
COPY src ./src/
RUN yarn build

FROM nginx:1.21-alpine

RUN rm -fr /usr/share/nginx/html/*
COPY --from=build /app/build /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
