#version 330
#extension GL_ARB_separate_shader_objects : require

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
#include <minecraft:fog.glsl>
#endif

#include <minecraft:dynamictransforms.glsl>
#include <minecraft:oit.glsl>

uniform sampler2D Sampler0;

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
layout(location = 0) in float sphericalVertexDistance;
layout(location = 1) in float cylindricalVertexDistance;
#endif

layout(location = 2) in vec4 vertexColor;
layout(location = 3) in vec2 texCoord0;

#ifndef OIT_ALPHA_ONLY
layout(location = 0) out vec4 fragColor;
#endif

vec4 calculateFinalColor(vec4 color) {
    #ifdef OIT_ACCUMULATE
    color = sampleColorForAccumulation(color);
    #endif

    #if !defined(IS_SEE_THROUGH) && !defined(IS_GUI)

    #ifdef OIT_ACCUMULATE
    vec4 fogColor = vec4(FogColor.rgb * color.a, FogColor.a);
    #else
    vec4 fogColor = FogColor;
    #endif

    color = apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, fogColor);
    #endif

    return color;
}

#include <minecraft:globals.glsl>
layout(location = 4) flat in int fpvMode;
layout(location = 5) flat in float fpvNoise;
layout(location = 6) in vec2 fpvScreen;

float fpvHash(vec3 point) {
    point = fract(point * 0.1031);
    point += dot(point, point.yzx + 33.33);
    return fract((point.x + point.y) * point.z);
}

vec4 interference() {
    float frame = floor(GameTime * 24000.0 * 1.5);
    vec2 pixel = floor(fpvScreen * ScreenSize * 0.7);
    float grain = fpvHash(vec3(pixel, frame));
    float row = fpvHash(vec3(floor(pixel.y / 2.0), frame, 7.0));
    float coarse = fpvHash(vec3(floor(pixel.x / 18.0), floor(pixel.y / 3.0), frame));
    float roll = fract(fpvScreen.y - frame * 0.013);
    float band = (1.0 - smoothstep(0.0, 0.07, abs(roll - 0.5))) * fpvNoise;
    float snow = clamp(grain * 0.72 + row * 0.19 + coarse * 0.15, 0.0, 1.0);
    float gray = mix(0.08, snow, 0.8) + band * 0.18;
    float strength = pow(fpvNoise, 1.35);
    float alpha = strength * (0.30 + grain * 0.50) + band * 0.28;
    alpha = mix(alpha, 0.99, smoothstep(0.86, 1.0, fpvNoise));
    float scan = step(0.66, fract(gl_FragCoord.y / 3.0));
    gray *= 1.0 - scan * 0.28;
    float edge = smoothstep(0.28, 0.72, length(fpvScreen - 0.5));
    alpha = max(alpha, edge * 0.07);
    vec3 rgb = mix(vec3(0.0), vec3(gray * 0.94, gray, gray * 0.96), min(fpvNoise * 8.0, 1.0));
    vec2 border = min(fpvScreen, 1.0 - fpvScreen);
    bool bracket = (border.x > 0.018 && border.x < 0.020 && border.y > 0.025 && border.y < 0.075)
        || (border.y > 0.025 && border.y < 0.028 && border.x > 0.018 && border.x < 0.055);
    if (bracket && fpvNoise < 0.9) {
        rgb = vec3(0.85, 0.92, 0.80);
        alpha = 0.7;
    }
    return vec4(rgb, clamp(alpha, 0.0, 1.0) * vertexColor.a);
}

void main() {
#if defined(IS_GUI) && !defined(OIT_ALPHA_ONLY)
    if (fpvMode == 2) {
        fragColor = interference() * ColorModulator;
        return;
    }
#endif

    #ifdef IS_GRAYSCALE
    vec4 texColor = texture(Sampler0, texCoord0).rrrr;
    #else
    vec4 texColor = texture(Sampler0, texCoord0);
    #endif

    vec4 color = texColor * vertexColor * ColorModulator;

    if (color.a < 0.1) {
        discard;
    }

    #ifdef OIT_ALPHA_ONLY
    executeAlphaOnlyPhase(gl_FragCoord.z, color.a);
    #else
    fragColor = calculateFinalColor(color);
    #endif
}
