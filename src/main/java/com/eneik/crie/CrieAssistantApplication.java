package com.eneik.crie;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.eneik.crie", "com.eneik.telemetry"})
public class CrieAssistantApplication {
    public static void main(String[] args) {
        SpringApplication.run(CrieAssistantApplication.class, args);
    }
}
