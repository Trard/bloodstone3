#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>

uniform sampler2D Sampler0;

in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec4 vertexColor;
in vec2 texCoord0;

out vec4 fragColor;

#moj_import <minecraft:globals.glsl>
flat in ivec2 sceneOrigin;
flat in float joinOpacity;
in vec2 sceneLocal;

vec4 renderSceneTile() {
    vec2 at = (gl_FragCoord.xy / ScreenSize - 0.5) * vec2(1.78, 1.88);
    float light = max(0.0, 1.0 - length(at)/1.24);
    float dither = fract(dot(gl_FragCoord.xy, vec2(0.754877666,0.569840296))) - 0.5;
    vec3 bg = (vec3(13,11,14) + pow(light,1.70) * vec3(62,13,18) + dither) / 255.0;
    if (any(lessThan(sceneLocal,vec2(0.0))) || any(greaterThan(sceneLocal,vec2(1.0)))) return vec4(bg,1.0);
    const ivec2 extent = ivec2(232,70);
    vec2 pos = clamp(sceneLocal * vec2(extent) - 0.5,vec2(0.0),vec2(extent-1));
    ivec2 lo = sceneOrigin+ivec2(floor(pos));
    ivec2 hi = min(lo+1,sceneOrigin+extent-1);
    vec2 w = fract(pos);
    vec4 a = texelFetch(Sampler0,lo,0), b = texelFetch(Sampler0,ivec2(hi.x,lo.y),0);
    vec4 c = texelFetch(Sampler0,ivec2(lo.x,hi.y),0), d = texelFetch(Sampler0,hi,0);
    vec3 upper = mix(mix(bg,a.rgb,a.a),mix(bg,b.rgb,b.a),w.x);
    vec3 lower = mix(mix(bg,c.rgb,c.a),mix(bg,d.rgb,d.a),w.x);
    return vec4(mix(upper,lower,w.y),1.0);
}

void main() {
    if (sceneOrigin.x >= 0) { fragColor = renderSceneTile(); fragColor.a = joinOpacity; return; }
    vec4 color = texture(Sampler0, texCoord0) * vertexColor * ColorModulator;
    if (color.a < 0.1) {
        discard;
    }
    fragColor = apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, FogColor);
}
