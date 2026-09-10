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

out vec4 fragColor;

void main() {
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
