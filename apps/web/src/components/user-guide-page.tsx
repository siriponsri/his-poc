import {UserGuide} from './user-guide'
import {GUIDE_CHAPTERS,GUIDE_DOMAINS} from '../data/user-guide-content'
import {GUIDE_MEDIA} from '../data/user-guide-media'

export default function UserGuidePage({roles=[]}:{roles?:string[]}){
 return <UserGuide chapters={GUIDE_CHAPTERS} domains={GUIDE_DOMAINS} media={GUIDE_MEDIA} roles={roles}/>
}
