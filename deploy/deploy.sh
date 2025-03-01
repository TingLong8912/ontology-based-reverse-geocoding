#!/bin/bash
NAMESPACE=tw-sgis
APP=tw-sgis-geospatialdescription
URL=geospatialdescription.sgis.tw
IMG=dkr.tw/sgis/geospatialdescription:api
IMGPORT=5000


cat << EOF | kubectl apply -n ${NAMESPACE} -f - || echo 1
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ${APP}-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
    ingress.kubernetes.io/ssl-redirect: "true"
    ingress.kubernetes.io/browser-xss-filter: "true" # X-XSS-Protection: 1; mode=block
    ingress.kubernetes.io/content-type-nosniff: "true" # X-Content-Type-Options: nosniff
  labels:
    app: ${APP}
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - ${URL}
    secretName: ${NAMESPACE}-secret
  rules:
  - host: ${URL}
    http:
      paths:
      - path: "/"
        pathType: Prefix
        backend:
          service:
            name: ${APP}-service
            port:
              number: ${IMGPORT}
---
apiVersion: v1
kind: Service
metadata:
  name: ${APP}-service
  annotations:
    loadbalancer.openstack.org/proxy-protocol: "true"
  labels:
    app: ${APP}
spec:
  ports:
  - name: web
    protocol: TCP
    port: ${IMGPORT}
    targetPort: ${IMGPORT}
  selector:
    app: ${APP}
  type: LoadBalancer
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP}
  labels:
    app: ${APP}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${APP}
  template:
    metadata:
      labels:
        app: ${APP}
    spec:
      imagePullSecrets:
        - name: registrykey-dkr-tw
      containers:
      - name: ${APP}-web
        image: ${IMG}
        imagePullPolicy: Always
        ports:
        - name: web
          containerPort: ${IMGPORT}
        volumeMounts:
        - name: localtime
          mountPath: /etc/localtime
      volumes:
      - name: localtime
        hostPath:
          #realpath /etc/localtime
          path: /usr/share/zoneinfo/Asia/Taipei
EOF

kubectl -n ${NAMESPACE} patch Deployment ${APP} -p "{\"spec\":{\"template\":{\"metadata\":{\"labels\":{\"date\":\"`date +'%s'`\"}}}}}"
