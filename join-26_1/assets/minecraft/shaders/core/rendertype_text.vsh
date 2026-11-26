#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>
#moj_import <minecraft:sample_lightmap.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV2;

uniform sampler2D Sampler2;

out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
out vec2 texCoord0;

uniform sampler2D Sampler0;
flat out ivec2 sceneOrigin;
flat out float joinOpacity;
out vec2 sceneLocal;

bool expandSceneTile() {
    ivec3 ink = ivec3(round(Color.rgb * 255.0));
    if (ink.r != 0 || ink.g != 0 || (ink.b != 170 && ink.b != 42) || ProjMat[3][3] != 1.0) return false;
    const ivec2 cell = ivec2(234, 72);
    const vec2 grid = vec2(2,1);
    ivec2 size = textureSize(Sampler0, 0);
    ivec2 edge = ivec2(round(UV0 * vec2(size)));
    for (int y = 0; y < 2; ++y) {
        for (int x = 0; x < 2; ++x) {
            ivec2 corner = ivec2(x,y);
            ivec2 at = edge - corner;
            if (any(lessThan(at, ivec2(0))) || any(greaterThanEqual(at,size))) continue;
            ivec4 tag = ivec4(round(texelFetch(Sampler0, at, 0)*255.0));
            if (tag.r != 127 || tag.g != 55 || tag.b >= 2 || tag.a != 255) continue;
            ivec2 origin = edge - corner * cell;
            if (any(lessThan(origin, ivec2(0))) || any(greaterThan(origin+cell,size))) continue;
            if (ivec4(round(texelFetch(Sampler0, origin, 0)*255.0)) != tag ||
                ivec4(round(texelFetch(Sampler0, origin+cell-1, 0)*255.0)) != tag) continue;
            sceneOrigin = origin + 1;
            joinOpacity = Color.a;
            if (ink.b == 42) {
                gl_Position = vec4(3,3,0,1);
                sceneLocal = vec2(0.0);
                return true;
            }
            ivec2 tile = ivec2(tag.b,0);
            vec2 guiSize = abs(vec2(2.0 / ProjMat[0][0], 2.0 / ProjMat[1][1]));
            vec2 artSize = vec2(1.0,70.0/464.0) * min(guiSize.x*0.62,guiSize.y*0.47);
            vec2 tileSize = artSize/grid;
            vec2 begin = (guiSize-artSize)*0.5 + vec2(tile)*tileSize;
            vec2 point = begin + vec2(corner)*tileSize;
            if (tile.x+x == 0) point.x = 0.0;
            if (tile.x+x == 2) point.x = guiSize.x;
            if (tile.y+y == 0) point.y = 0.0;
            if (tile.y+y == 1) point.y = guiSize.y;
            sceneLocal = (point-begin)/tileSize;
            gl_Position.xy = (ProjMat * vec4(point,0,1)).xy * gl_Position.w;
            gl_Position.z = 0.0;
            return true;
        }
    }
    return false;
}

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
    sceneOrigin = ivec2(-1);
    joinOpacity = 0.0;
    if (expandSceneTile()) return;

    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color * sample_lightmap(Sampler2, UV2);
    texCoord0 = UV0;
}
