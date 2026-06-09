FROM tomcat:9.0-jdk17-temurin

RUN rm -rf /usr/local/tomcat/webapps/* \
    && mkdir -p /usr/local/tomcat/webapps/nitzan_tomer_yonatan_devops_project

COPY simple.jsp /usr/local/tomcat/webapps/nitzan_tomer_yonatan_devops_project/index.jsp
COPY simple.jsp /usr/local/tomcat/webapps/nitzan_tomer_yonatan_devops_project/simple.jsp

EXPOSE 8080

CMD ["catalina.sh", "run"]
