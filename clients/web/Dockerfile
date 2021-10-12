FROM node:14-alpine as build

WORKDIR /app

ADD package.json yarn.lock ./
RUN yarn

ADD public ./public/
ADD src ./src/
RUN yarn build

FROM nginx:1.21-alpine

RUN rm -fr /usr/share/nginx/html/*
COPY --from=build /app/build /usr/share/nginx/html

CMD ["nginx", "-g", "daemon off;"]
