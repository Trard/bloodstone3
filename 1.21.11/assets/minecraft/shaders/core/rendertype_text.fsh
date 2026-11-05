#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:globals.glsl>

uniform sampler2D Sampler0;

in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec4 vertexColor;
in vec2 texCoord0;
in vec2 bseScreenPosition;
flat in int bseLetterbox;
flat in int bseScare;
flat in int bseCameraPhase;
flat in int bseCameraSeed;
flat in int invasionBranding;
flat in ivec2 invasionBrandingOrigin;

flat in int fpvMode;
flat in float fpvNoise;
in vec2 fpvScreen;

out vec4 fragColor;

vec4 brandingTexel(ivec2 at) {
    vec4 value = texelFetch(Sampler0, clamp(at, invasionBrandingOrigin,
        invasionBrandingOrigin + ivec2(254, 38)), 0);
    return vec4(value.rgb * value.a, value.a);
}

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
    if (fpvMode == 2) {
        fragColor = interference() * ColorModulator;
        return;
    }
    if (fpvMode == 1) {
        vec4 color = texture(Sampler0, texCoord0) * vertexColor * ColorModulator;
        if (color.a < 0.1) discard;
        fragColor = color;
        return;
    }

    if (invasionBranding == 1) {
        // Smooth only the HD logo; glyphs and faction flags stay pixel sharp.
        vec2 at = texCoord0 * vec2(textureSize(Sampler0, 0)) - 0.5;
        ivec2 pixel = ivec2(floor(at));
        vec2 weight = fract(at);
        vec4 value = mix(mix(brandingTexel(pixel), brandingTexel(pixel + ivec2(1,0)), weight.x),
                         mix(brandingTexel(pixel + ivec2(0,1)), brandingTexel(pixel + ivec2(1,1)), weight.x), weight.y);
        if (value.a < 0.003) discard;
        fragColor = vec4(value.rgb / value.a, value.a) * vertexColor * ColorModulator;
        return;
    }
    if (bseCameraPhase >= 0) {
        float value = 0.0;
        vec2 at = abs(bseScreenPosition);
        if (bseCameraPhase == 0) {
            // Camera power-off: picture collapses to a horizontal line.
            value = at.x < 0.97 && at.y < 0.012 ? 0.88 : 0.0;
        } else if (bseCameraPhase == 1) {
            value = at.x < 0.24 && at.y < 0.004 ? 0.80 : 0.0;
        } else if (bseCameraPhase == 2) {
            value = at.x < 0.002 && at.y < 0.003 ? 0.5 : 0.0;
        } else {
            // Screen-pixel-sized dots, independent of GUI scale/aspect ratio.
            // Integer hashing avoids texture-atlas limits and extra uniforms.
            uvec2 cell = uvec2(gl_FragCoord.xy) / 2u;
            uint n = cell.x * 1597334677u ^ cell.y * 3812015801u ^ uint(bseCameraSeed + 1) * 2798796415u;
            n ^= n >> 16; n *= 2246822519u; n ^= n >> 13;
            value = (n & 1u) == 0u ? 0.015 : 0.92;
        }
        fragColor = vec4(vec3(value), vertexColor.a * ColorModulator.a);
        return;
    }
    if (bseScare == 1) {
        vec4 image = texture(Sampler0, texCoord0);
        image.a *= vertexColor.a * ColorModulator.a;
        if (image.a < 0.01) discard;
        fragColor = image;
        return;
    }
    if (bseLetterbox == 1) {
        // 11% of the real viewport at each edge. The middle remains untouched.
        if (abs(bseScreenPosition.y) < 0.78) discard;
        fragColor = vec4(0.0, 0.0, 0.0, vertexColor.a * ColorModulator.a);
        return;
    }
    // Original Minecraft 1.21.11 text rendering for all other glyphs.
    vec4 color = texture(Sampler0, texCoord0) * vertexColor * ColorModulator;
    if (color.a < 0.1) discard;
    fragColor = apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance,
        FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, FogColor);
}
