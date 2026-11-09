package com.eneik.crie.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class WebViewController {

    @GetMapping({"/", "/crie", "/crie/"})
    public String index() {
        return "forward:/index.html";
    }
}
