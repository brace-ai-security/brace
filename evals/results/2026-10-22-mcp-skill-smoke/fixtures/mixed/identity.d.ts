export declare function verifiedJwtClaims(token: string): Promise<{azp:string; scopes:string[]; exp:number; aud:string}>;
