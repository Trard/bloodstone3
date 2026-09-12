#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>

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

out vec4 fragColor;

void main() {
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
