import { Config } from "@remotion/cli/config";

Config.setEntryPoint("src/index.ts");
Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(90);
// Codificação pela GPU (RTX 4060) quando possível.
Config.setHardwareAcceleration("if-possible");
Config.setOverwriteOutput(true);
