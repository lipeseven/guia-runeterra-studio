import { Config } from "@remotion/cli/config";

Config.setEntryPoint("src/index.ts");
Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(92);
Config.setChromiumOpenGlRenderer("angle"); // WebGL (three.js) pela GPU
Config.setOverwriteOutput(true);
