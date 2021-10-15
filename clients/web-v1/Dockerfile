FROM nginx:1.21-alpine

RUN rm -fr /usr/share/nginx/html/*
COPY ./reader /usr/share/nginx/html/v1/reader

COPY ./nginx.conf /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
